# Task A - Inventory Reservation Ledger

## Overview

This task implements a deterministic command processor for a single SKU.

The system tracks:

- `on_hand`: current physical stock in the warehouse.
- `reservations`: the quantity currently reserved by each order.
- `reserved_total`: the total quantity reserved across all orders.
- `processed_events`: event IDs that have already been processed.

Available stock is calculated as:

```text
available = on_hand - reserved_total
```

## Supported Commands

### RESERVE

```text
RESERVE event_id order_id qty
```

Reserves `qty` units for the specified order.

The command succeeds only when enough available stock exists.

### RELEASE

```text
RELEASE event_id order_id qty
```

Releases `qty` units from the order's current reservation.

The command is rejected when the release quantity exceeds the current reserved quantity for that order.

### SHIP

```text
SHIP event_id order_id qty
```

Ships `qty` units for the specified order.

The command is rejected when the shipping quantity exceeds the order's current reserved quantity.

A successful shipment decreases both:

- `on_hand`
- the order's reserved quantity

### RESTOCK

```text
RESTOCK event_id qty
```

Adds `qty` units to the warehouse's physical stock.

This command does not change any order's reservation.

## Validation and Idempotency

All quantities must be positive integers within the required range.

Malformed commands are rejected before any state changes are made.

`event_id` values are idempotent. If an event ID has already been processed, the command returns:

```text
DUPLICATE
```

and the current state is not changed.

A valid business operation that is rejected is still considered processed. Therefore, replaying the same rejected `event_id` also returns `DUPLICATE`.

## Output

For every command, the program prints:

```text
STATUS on_hand reserved_total
```

where `STATUS` is one of:

- `OK`
- `REJECTED`
- `DUPLICATE`

After all commands are processed, the program prints the remaining open reservations sorted by `order_id`.

Example:

```text
OPEN 2
o100 3
o200 5
```

## Running the Program

From the repository root:

```bash
python A/solution.py
```

Example input:

```text
10 6
RESERVE e1 o100 4
RESERVE e2 o200 7
SHIP e3 o100 2
RELEASE e4 o100 2
RESTOCK e5 3
RESERVE e2 o999 1
```

Expected output:

```text
OK 10 4
REJECTED 10 4
OK 8 2
OK 8 0
OK 11 0
DUPLICATE 11 0
OPEN 0
```

## Running Tests

Task A includes automated tests covering normal behaviour, edge cases, validation failures, replay/idempotency, and output ordering.

Run the tests with:

```bash
python A/test_solution.py
```

Or with unittest discovery:

```bash
python -m unittest discover -s A -p "test_solution.py"
```

## Test Coverage

The test suite covers:

- official sample behaviour
- duplicate successful events
- replay of rejected business operations
- insufficient stock for `RESERVE`
- excessive `RELEASE`
- excessive `SHIP`
- correct `SHIP` state changes
- `RESTOCK`
- removing orders after all reserved quantity is released
- sorted open reservations
- malformed quantities
- zero and negative quantities
- incorrect argument counts
- unknown commands
- non-ASCII `event_id`
- non-ASCII `order_id`
- quantity limits
- maximum valid quantity

## Complexity

Each command is processed in average **O(1)** time because reservations are stored in a dictionary and processed event IDs are stored in a set.

At the end, open reservations are sorted by `order_id`, which takes **O(K log K)** time, where `K` is the number of open orders.

**Overall time complexity:** `O(N + K log K)`

**Space complexity:** `O(N + K)`

where:

- `N` is the number of commands.
- `K` is the number of open orders at the end.

## Assumptions

- Input is provided through standard input.
- The first line contains the initial stock and the number of commands.
- Event IDs and order IDs must be non-empty ASCII tokens.
- Malformed input does not modify inventory state.
- Rejected business operations are recorded as processed events for idempotency.

## AI Usage Disclosure

AI-assisted tools were used during this assessment for:

- clarifying task requirements and edge cases
- brainstorming test cases
- reviewing code structure and potential failure cases
- improving documentation wording

The submitted implementation was reviewed and tested by the candidate. The candidate is responsible for the final implementation and can explain the state management, validation rules, idempotency logic, test cases, and complexity analysis.

No credentials, API keys, or real customer data were used.
