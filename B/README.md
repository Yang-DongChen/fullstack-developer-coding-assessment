# Task B - Fulfilment Split Optimiser

## Problem Summary

Given multiple warehouses and an order quantity `Q`, allocate exactly `Q` units while following these priorities:

1. Minimise the number of warehouses used.
2. Then minimise total shipping cost.
3. Then choose the lexicographically smallest allocation list sorted by `warehouse_id`.

For each used warehouse:

```text
shipping cost = fixed_cost + allocated_qty * unit_cost

If the order cannot be fulfilled exactly, the program outputs:

-1
Solution Approach

The solution uses dynamic programming.

dp[q] represents the best solution for producing exactly q units using the warehouses processed so far.

Each state stores:

(number of warehouses used, total cost, allocation)

Solutions are compared in the same order as the requirements:

1. fewer warehouses
2. lower total cost
3. lexicographically smaller allocation

The implementation uses a sliding-window optimisation for the warehouse quantity transition so that it can handle the given constraints without brute-force enumeration of warehouse subsets.

Complexity

Let:

W = number of warehouses
Q = requested quantity

The main DP processes O(W * Q) states.

Because allocation lists are stored for lexicographical tie-breaking, the worst-case complexity is:

Time: O(W^2 * Q)
Space: O(W * Q)
Running

From the repository root:

python B/solution.py

Example:

python B/solution.py < input.txt
Tests

Run:

pytest B/test_solution.py -v

The tests cover:

official sample
impossible orders
zero-stock warehouses
minimum warehouse count
minimum shipping cost
lexicographical tie-breaking
split allocations
large quantities
unsorted warehouse input
```
