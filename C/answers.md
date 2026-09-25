# Task C - Xero Integration Review

## Assumptions

- I use the current Xero OAuth 2.0 flow and Xero Accounting API 2.0 REST API.
- I use raw HTTPS requests rather than a language SDK, so the design is independent of a specific SDK version.
- For new applications, I assume the granular invoice scope `accounting.invoices`. Older applications may still use the broader `accounting.transactions` scope during Xero's migration period.
- Each connected organisation stores its own `tenant_id`, token data, and sync cursor.

## C1 - Connection verification

I would use the smallest sequence below and stop before reading invoices if a check fails.

1. **Get a valid access token.**
   - If the stored access token is still valid, use it.
   - If it is expired, refresh it first.
   - Confirm the token has the permission needed to access invoices.

2. **Call `GET https://api.xero.com/connections`.**
   - Send `Authorization: Bearer <access_token>`.
   - Find the connected organisation whose `id` equals the stored `tenant_id`.
   - This proves that the OAuth connection is usable and that the expected tenant is still connected.

3. **Only then call the invoices endpoint.**
   - For the normal user-authorisation flow, send `Authorization` and `xero-tenant-id`.
   - Call `GET /api.xro/2.0/Invoices?page=1`.
   - A `200` proves that authentication, tenant selection, endpoint configuration and invoice access work together.

```text
stored connection
    |
    +-- access token valid? -- no --> refresh token --> save new tokens
    |                                  |
    |                                  +-- refresh fails --> re-authorise
    |
    +-- check required invoice scope
    |
    +-- GET /connections
    |       |
    |       +-- stored tenant_id found? -- no --> connection/config error
    |
    +-- GET /api.xro/2.0/Invoices?page=1
```

## C2 - Failure diagnosis

```text
GET /connections = 200
        |
        +--> GET /Invoices
                |
                +-- 401 Unauthorized
                |     1. Check access-token expiry/validity.
                |     2. Refresh the access token once.
                |     3. Inspect `WWW-Authenticate` when present.
                |     4. If it indicates `insufficient_scope`, check `accounting.invoices`.
                |     5. If the problem remains, mark the connection for re-authorisation.
                |
                +-- 403 Forbidden
                |     1. Check the Xero user's permission to access the organisation/data.
                |     2. Compare user permissions between working and failing environments.
                |     3. Do not keep retrying a persistent permission failure.
                |
                +-- 404 Not Found
                      1. Check endpoint URL and API version.
                      2. Check `xero-tenant-id` against the current `/connections` result.
                      3. Check that the organisation is still connected.
                      4. Compare environment variables/configuration.
                      5. Do not blindly retry; fix the resource or configuration first.
```

For environment differences, I would compare the **client ID, client secret, redirect URI, requested scopes, stored tenant ID, API base URL, and connection data**. I would also verify that the test environment is connected to the intended Xero demo/test organisation.

Current Xero documentation distinguishes invalid authorisation (`401`), permission failures (`403`) and missing resources (`404`). Xero's current granular-scope guidance also says an endpoint called without the required granular scope can return `401` with `WWW-Authenticate: insufficient_scope`; therefore, scope diagnosis should not be limited to `403`.

## C3 - Incremental synchronisation

For a large organisation I would make the sync resumable and idempotent.

### Initial sync

1. Start a sync job and save a sync record for `(tenant_id, job_id)`.
2. Request invoices page by page.
3. Process each page and upsert invoices using `(tenant_id, invoice_id)` as the unique key.
4. Save the current page/checkpoint only **after that page is committed successfully**.
5. Continue until there are no more pages.

### Incremental sync

Use Xero's `If-Modified-Since` header so only invoices changed since the previous watermark need to be fetched.

Example:

```http
GET https://api.xero.com/api.xro/2.0/Invoices?page=1
Authorization: Bearer <access_token>
xero-tenant-id: <tenant_id>
If-Modified-Since: 2026-09-25T00:00:00Z
Accept: application/json
```

I would keep a small overlap in the watermark, for example re-reading from a few seconds before the last successful watermark. This can produce duplicates, so the database must make replay safe with a unique `(tenant_id, invoice_id)` key.

A safe rule is:

```text
job_start = now
read changes since (last_watermark - small_overlap)
process all pages
only after the whole job succeeds:
    last_watermark = job_start
```

This avoids moving the watermark past records that changed while the job was running.

### Partial failure and replay

- If page 7 fails, keep the cursor at the last successfully committed checkpoint and retry from there.
- If the worker dies, restart from the saved cursor.
- Reprocessing a successful page is acceptable because upsert + unique keys prevent duplicates.
- Save cursor and processed data in one database transaction when possible.
- Never advance the cursor before the corresponding data is durably saved.

## C4 - Rate limits

When Xero returns `429 Too Many Requests`:

1. Read `Retry-After` and wait at least that many seconds.
2. Read the rate-limit headers to understand whether the minute/day/app limit is being reached.
3. Add exponential backoff plus random jitter for repeated retries.
4. Limit worker concurrency per tenant.
5. Use a small retry budget, for example 3 retries for one job, then reschedule the job instead of retrying forever.

Example:

```python
for attempt in range(3):
    response = call_xero()

    if response.status_code == 200:
        return response

    if response.status_code == 429:
        wait_seconds = int(response.headers.get("Retry-After", "5"))
        wait_seconds += random_jitter()
        sleep(wait_seconds)
        continue

    if response.status_code == 401:
        refresh_token_once()
        continue

    if response.status_code in (500, 503):
        sleep(exponential_backoff(attempt) + random_jitter())
        continue

    if response.status_code in (400, 403, 404):
        raise PermanentError()

    raise UnexpectedError()
```

I would not automatically retry validation/configuration errors such as `400`, permission errors such as `403`, or missing resources such as `404`. A `401` gets one token-refresh/re-authorisation path, not an unlimited retry loop. Transient `5xx/503` errors can use the same bounded retry mechanism.

## C5 - Data integrity

The main risk is:

```text
Create invoice -> Xero succeeds -> network times out -> worker thinks it failed -> retries
```

I would use **idempotency + local mapping + reconciliation**.

### Before creating the invoice

Create a local record like:

```text
order_id -> tenant_id -> status=PENDING -> idempotency_key
```

Put the same stable idempotency key on the Xero create request:

```http
Idempotency-Key: <stable-key-for-this-create-operation>
```

If the request times out, retry with the **same key** while the key is still valid.

### After a successful response

Save the returned `InvoiceID` in the local database:

```text
(order_id, tenant_id) UNIQUE
(order_id, tenant_id) -> xero_invoice_id
```

### If the response is lost

1. Retry with the same idempotency key if it is still valid.
2. If the key has expired, first reconcile by querying Xero using a deterministic business identifier controlled by the integration, such as a unique invoice number.
3. If the invoice exists, store its Xero `InvoiceID` instead of creating another invoice.
4. Only create a new invoice when reconciliation confirms that no matching invoice exists.

This makes normal worker retries safe and prevents a timeout from creating duplicate invoices.

## C6 - Observability and security

### Logs

Log:

- `job_id`
- `tenant_id` (or a safe hashed form if needed)
- internal `order_id`
- Xero `InvoiceID` when known
- Xero correlation ID when returned
- HTTP method and endpoint name
- status code
- latency
- retry count
- sync page/cursor
- error category

Never log:

- access tokens
- refresh tokens
- client secrets
- `Authorization` headers
- full request/response bodies containing customer or financial data

### Metrics

I would track:

```text
xero_requests_total{endpoint,status}
xero_request_latency_seconds
xero_429_total
xero_401_total
xero_403_total
xero_5xx_total
xero_token_refresh_failures_total
xero_sync_records_total
xero_sync_failures_total
xero_sync_lag_seconds
xero_duplicate_prevented_total
```

### Alerts

Alert on sustained 429s, repeated 401/token-refresh failures, repeated 5xx errors, growing sync lag, and jobs stuck at the same cursor for too long.

### Secrets and rotation

Store client secrets and tokens in a dedicated secret store or encrypted database, not in source code or normal logs. Use least-privilege access and separate credentials by environment.

Xero access tokens expire after 30 minutes. Refresh tokens, when using the standard OAuth flow, should be securely replaced with the newly returned refresh token after a successful refresh. A connection that can no longer be refreshed should be sent through authorisation again.

## Official Xero references

- OAuth 2.0 token types: https://developer.xero.com/documentation/guides/oauth2/token-types/
- OAuth 2.0 scopes: https://developer.xero.com/documentation/guides/oauth2/scopes/
- OAuth 2.0 / PKCE flow: https://developer.xero.com/documentation/guides/oauth2/pkce-flow/
- Accounting API - Invoices: https://developer.xero.com/documentation/api/accounting/invoices
- Accounting API - response codes: https://developer.xero.com/documentation/api/accounting/responsecodes
- Idempotent requests: https://developer.xero.com/documentation/guides/idempotent-requests/idempotency/
- Rate limits: https://developer.xero.com/documentation/best-practices/api-call-efficiencies/rate-limits/
- Granular scopes FAQ: https://developer.xero.com/faq/granular-scopes
- Developer changelog: https://developer.xero.com/changelog

## SDK / API version assumption

This answer intentionally does **not** depend on a specific SDK. The examples use the current documented Xero Accounting API 2.0 REST endpoints and standard HTTP behaviour, so the same logic can be implemented with Python `requests`, another HTTP client, or a current Xero SDK.
