from collections import deque
import sys


# 一个方案：
# (使用仓库数量, 总成本, 分配列表)
Plan = tuple[int, int, tuple[int, ...]]


def parse_input(text: str):
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]

    if not lines:
        raise ValueError("Input is empty")

    # 第一行：W Q
    first_line = lines[0].split()

    if len(first_line) != 2:
        raise ValueError("First line must contain W and Q")

    W, Q = map(int, first_line)

    if not 1 <= W <= 30:
        raise ValueError("W must be between 1 and 30")

    if not 1 <= Q <= 2000:
        raise ValueError("Q must be between 1 and 2000")

    if len(lines) != W + 1:
        raise ValueError("Warehouse count does not match W")

    warehouses = []

    for line in lines[1:]:
        parts = line.split()

        if len(parts) != 4:
            raise ValueError(
                "Each warehouse line must contain 4 fields"
            )

        warehouse_id, stock_text, fixed_text, unit_text = parts

        if not warehouse_id.isascii():
            raise ValueError("warehouse_id must be ASCII")

        stock = int(stock_text)
        fixed_cost = int(fixed_text)
        unit_cost = int(unit_text)

        if not 0 <= stock <= 2000:
            raise ValueError("stock must be between 0 and 2000")

        if not 0 <= fixed_cost <= 10**6:
            raise ValueError(
                "fixed_cost must be between 0 and 10^6"
            )

        if not 0 <= unit_cost <= 10**6:
            raise ValueError(
                "unit_cost must be between 0 and 10^6"
            )

        warehouses.append(
            {
                "id": warehouse_id,
                "stock": stock,
                "fixed_cost": fixed_cost,
                "unit_cost": unit_cost,
            }
        )

    # 最后需要按照 warehouse_id 排序。
    warehouses.sort(key=lambda warehouse: warehouse["id"])

    return W, Q, warehouses


def solve(text: str) -> str:
    _, Q, warehouses = parse_input(text)

    # dp[q]：
    # 使用已经处理过的仓库，刚好得到 q 件商品时的最佳方案。
    #
    # None 表示暂时无法刚好得到 q 件。
    dp: list[Plan | None] = [None] * (Q + 1)

    # 凑出 0 件，不需要使用任何仓库。
    dp[0] = (0, 0, ())

    for warehouse in warehouses:
        stock = warehouse["stock"]
        fixed_cost = warehouse["fixed_cost"]
        unit_cost = warehouse["unit_cost"]

        new_dp: list[Plan | None] = [None] * (Q + 1)

        # 保存当前 q 可以使用的旧状态。
        window = deque()

        for q in range(Q + 1):
            previous_q = q - 1

            # 当前仓库至少要发 1 件，
            # 所以 previous_q 必须小于 q。
            if previous_q >= 0 and dp[previous_q] is not None:
                old_count, old_cost, old_allocation = dp[previous_q]

                # 对固定的 q：
                #
                # old_cost + fixed_cost
                # + (q - previous_q) * unit_cost
                #
                # 可以写成：
                #
                # old_cost - previous_q * unit_cost
                #
                # 后面的部分对于当前 q 都相同。
                key = (
                    old_count,
                    old_cost - previous_q * unit_cost,
                    old_allocation,
                )

                while window and key < window[-1][1]:
                    window.pop()

                window.append((previous_q, key))

            # 当前仓库最多只能发 stock 件。
            min_previous_q = q - stock

            while window and window[0][0] < min_previous_q:
                window.popleft()

            # 情况 1：不使用当前仓库。
            if dp[q] is not None:
                old_count, old_cost, old_allocation = dp[q]

                new_dp[q] = (
                    old_count,
                    old_cost,
                    old_allocation + (0,),
                )

            # 情况 2：使用当前仓库。
            if window:
                best_previous_q = window[0][0]

                old_count, old_cost, old_allocation = dp[best_previous_q]

                allocated = q - best_previous_q

                candidate = (
                    old_count + 1,
                    old_cost + fixed_cost + allocated * unit_cost,
                    old_allocation + (allocated,),
                )

                # Python 元组会按照：
                # 1. 仓库数量
                # 2. 总成本
                # 3. allocation 字典序
                # 自动比较。
                if new_dp[q] is None or candidate < new_dp[q]:
                    new_dp[q] = candidate

        dp = new_dp

    # 无法刚好凑出 Q 件。
    if dp[Q] is None:
        return "-1\n"

    warehouse_count, total_cost, allocation = dp[Q]

    output = [
        f"{warehouse_count} {total_cost}"
    ]

    # allocation 顺序与排序后的 warehouses 一一对应。
    for warehouse, quantity in zip(warehouses, allocation):
        if quantity > 0:
            output.append(
                f"{warehouse['id']} {quantity}"
            )

    return "\n".join(output) + "\n"


def main() -> None:
    text = sys.stdin.read()
    sys.stdout.write(solve(text))


if __name__ == "__main__":
    main()