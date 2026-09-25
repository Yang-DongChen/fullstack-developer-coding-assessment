# Task C - Xero Integration Review

## Assumptions

- I assume the integration uses Xero's Accounting API v2 and standard OAuth 2.0 user-authorisation flow.
- I assume each connected organisation has its own stored Xero tenant ID and sync cursor.
- For new Xero apps created from 2 March 2026, I assume granular scopes are used, such as `accounting.invoices`. Older apps may still use the broader `accounting.transactions` scope during the migration period.
- The design is SDK-independent. An official Xero SDK can be used, but the checks and failure handling should remain the same.

## C1 - Connection verification

Before reading invoices, I would make the smallest verification sequence:

1. Make sure there is a valid access token.
   - Check that the token exists and has not expired.
   - Xero access tokens are valid for up to 30 minutes. If needed, refresh the token before continuing.

2. Call the Xero `GET /connections` endpoint using the access token.
   - `200 OK` proves that OAuth authentication is working and the token can access the Xero connections endpoint.
   - The response contains the connected tenant ID(s).

3. Compare the returned tenant ID with the tenant ID stored for this internal organisation.
   - Match = the application selected the expected Xero organisation.
   - No match = stop the sync and treat it as a tenant-selection/configuration problem.

4. Check that the OAuth token contains the scope required to read invoices.
   - For current granular scopes, the invoice permission is `accounting.invoices`.

5. Only then call `GET /Invoices` with:
   - `Authorization: Bearer <access_token>`
   - `xero-tenant-id: <tenant_id>` for the normal user-authorisation flow.

This gives a simple separation:

```text
Token valid?
    |
    v
GET /connections
    |
    v
Expected tenant ID?
    |
    v
Invoice scope available?
    |
    v
GET /Invoices
```

If any check fails, I would stop before reading invoices and record the reason for diagnosis.

## C2 - Failure diagnosis

I would use the following decision tree:

```text
GET /connections succeeds
        |
        v
GET /Invoices fails
        |
   +----+----+
   |         |
  401       403
   |         |
   v         v
Token     Scope / permission
problem    problem
   |
refresh/re-auth
```

### 401 Unauthorized

Check in this order:

1. Is the access token expired?
2. Was the refreshed token actually saved?
3. Is the `Authorization: Bearer ...` header correct?
4. Is the token from the expected Xero app/environment?

Action:

- Refresh the token and retry once.
- If refresh fails, mark the connection as requiring re-authentication instead of retrying forever.

### 403 Forbidden

Check:

1. Does the token contain the required invoice scope?
2. Was the application authorised with the new granular scope?
3. Does the Xero user have permission to access the required organisation/data?
4. Was the scope changed after the original authorisation?

Action:

- Do not repeatedly retry.
- Ask for the required permission/re-authorisation if necessary. Xero recommends requesting the minimum scopes required.

### 404 Not Found

Check:

1. Is the Xero tenant ID correct?
2. Was the tenant disconnected and later reconnected?
3. Is the worker using the correct environment/configuration?
4. Is the API endpoint/base URL correct?
5. Is the resource actually present?

Action:

- Stop the job, log the configuration problem, and verify the connection rather than blindly retrying.

### Environment checks

For each environment I would verify:

```text
XERO_CLIENT_ID
XERO_CLIENT_SECRET
XERO_API_BASE_URL
XERO_AUTH_URL
stored tenant_id
stored token set
requested scopes
```

The important rule is that credentials and tenant configuration must not be mixed between development, staging, and production.

## C3 - Incremental synchronisation

For a large organisation, I would use paginated incremental sync rather than downloading all invoices every time.

### Basic flow

```text
Read saved sync cursor
        |
        v
Request invoices modified since cursor
        |
        v
Process one page
        |
        v
Upsert invoices by Xero InvoiceID
        |
        v
Save progress
        |
        v
Request next page
        |
        v
Repeat until finished
```

Xero supports pagination for invoices and recommends using `If-Modified-Since` to retrieve only records changed since a given time. Pagination can retrieve invoices in batches of 100.

### Cursor

For each tenant I would store something like:

```text
tenant_id
last_successful_sync_at
page/checkpoint
sync_status
```

I would only move the main sync cursor forward after the corresponding page has been processed successfully.

### Duplicates

Use the Xero `InvoiceID` as a unique key in the internal database.

```text
if InvoiceID exists:
    update existing invoice
else:
    insert invoice
```

This makes the operation safe to replay.

### Change window

To reduce the risk of missing records near the cursor boundary, I would use a small overlap:

```text
next_start = last_successful_sync_at - overlap
```

For example, the next run can re-read a few minutes of data. Duplicate records are safe because the database uses an upsert/unique key.

### Partial failure

If page 5 succeeds and page 6 fails:

```text
Pages 1-5 = committed
Page 6 = failed
```

The worker should keep the last successful checkpoint and retry page 6 later. It should not mark the entire sync as successful.

### Safe replay

A replay should be harmless:

```text
same InvoiceID
      |
      v
upsert
      |
      v
one internal record
```

This allows worker crashes, retries, and overlapping change windows without creating duplicate internal invoices.

## C4 - Rate limits

If the worker receives `HTTP 429`, I would treat it as a temporary rate-limit response.

Xero provides rate-limit information in response headers, including remaining minute/day/app limits, and a 429 response includes `Retry-After` indicating how many seconds to wait.

### Handling

1. Read `Retry-After` if present.
2. Wait at least that long.
3. Add small random jitter.
4. Retry with exponential backoff if additional retries are allowed.
5. Limit worker concurrency so many jobs do not retry simultaneously.
6. Keep a retry budget, for example 3-5 attempts.
7. If the budget is exhausted, reschedule the job for later instead of continuously retrying.

Example:

```text
429
 |
 +--> Retry-After = 5s
 |
 wait 5s + jitter
 |
 retry
 |
 +--> 429 again
       |
       wait longer
       |
       retry until retry budget is reached
```

For large data sets, pagination and `If-Modified-Since` should also be used to reduce unnecessary API calls. Xero recommends queuing/scheduling background work for large retrieval jobs.

### Errors not blindly retried

I would not automatically retry these as normal transient failures:

```text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
```

These normally require correcting the request, token, permission, tenant, or resource configuration first.

Transient network failures and appropriate `5xx` responses can be retried with the same idempotency strategy where applicable.

## C5 - Data integrity

The main problem is:

```text
POST create invoice
      |
      v
Xero creates invoice successfully
      |
      v
response is lost / timeout
      |
      v
worker thinks it failed
      |
      v
worker retries
```

Without protection, this may create a duplicate invoice.

### Idempotency

For mutating requests, I would send a stable `Idempotency-Key` for the same logical operation.

Example:

```text
Idempotency-Key: order-12345-create-invoice
```

When the same request must be retried because of a timeout, I would reuse the same key rather than creating a new one. Xero uses the idempotency key to avoid processing the same mutation again and can return the cached original response.

### Internal database protection

I would also keep a record such as:

```text
order_id
xero_invoice_id
status
idempotency_key
```

and enforce a unique constraint on the business operation, for example:

```text
UNIQUE(order_id)
```

or an equivalent unique sync key.

### Lost response reconciliation

If a create request times out:

1. Retry with the same idempotency key when appropriate.
2. If the idempotency result cannot be confirmed, query Xero to check whether the invoice already exists.
3. If the invoice exists, save its Xero ID and mark the order as synced.
4. Only create a new invoice when there is evidence that the previous create did not succeed and the idempotency key can safely be replaced.

Xero specifically recommends inspecting the resource with a GET request when repeated idempotent requests continue to fail, before attempting a new creation.

## C6 - Observability and security

### Logs

For every sync job I would log:

```text
request_id
job_id
tenant_id
internal_order_id
xero_invoice_id
operation
HTTP status
duration_ms
retry_count
sync result
error category
```

Example:

```text
request_id=abc123
job_id=job456
tenant_id=tenant789
operation=invoice_sync
status=success
duration_ms=420
```

### Correlation IDs

I would use:

- `request_id` for tracing one API/request flow
- `job_id` for one background worker job
- `tenant_id` to identify the connected organisation
- `order_id` / `invoice_id` to connect business records

These IDs make it possible to trace:

```text
internal order
    -> worker job
    -> Xero API call
    -> Xero invoice
```

### Metrics

Useful metrics include:

```text
invoice_sync_success_total
invoice_sync_failure_total
invoice_sync_duration_seconds
xero_api_requests_total
xero_429_total
xero_401_total
xero_403_total
xero_5xx_total
sync_retry_total
```

I would also monitor queue depth and the age of the oldest pending sync job.

### Alerts

Examples:

- invoice sync failure rate becomes high
- repeated 401 responses
- repeated 403 responses
- sudden increase in 429 responses
- worker queue is growing for too long
- sync jobs are stuck or delayed

### What must never be logged

Never log:

```text
access_token
refresh_token
client_secret
passwords
Authorization header
full request bodies containing sensitive financial/customer data
```

Tokens and secrets should be masked or completely excluded from logs.

### Secret storage

Secrets should not be hard-coded in source code or committed to Git.

I would store them in:

```text
environment variables
or
a secret manager
```

For stored Xero tokens, use encrypted storage with restricted access.

### Rotation

Rotate application secrets regularly and replace compromised credentials immediately.

For OAuth tokens, refresh them according to Xero's OAuth flow and securely save the newly issued token data. Access tokens expire after 30 minutes; refresh tokens, when used in the standard OAuth flow, are also subject to Xero's token lifecycle.

## Official Xero documentation referenced

- Xero OAuth 2.0 / PKCE flow
- Xero Token Types
- Xero Rate Limits
- Xero Limits FAQ
- Xero Idempotent Requests
- Xero OAuth 2.0 Scopes / Granular Scopes

The implementation should be checked against the current Xero documentation before production deployment because Xero is migrating Accounting API permissions from broad scopes to granular scopes.
