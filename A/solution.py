MAX_QTY = 10**12


# 读取初始库存和命令数量
first_line = input().split()

initial_stock = int(first_line[0])
command_count = int(first_line[1])

# 当前仓库中的实际库存数量
on_hand = initial_stock

# 保存每个订单当前预留的数量
# 格式：order_id -> reserved_quantity
reservations = {}

# 保存已经处理过的 event_id
processed_events = set()

# 单独维护当前所有订单的预留总量
# 这样就不需要每处理一条命令都重新计算 sum(reservations.values())
reserved_total = 0


for _ in range(command_count):

    command = input()
    parts = command.split()

    # 空命令属于格式错误
    if not parts:
        print("REJECTED", on_hand, reserved_total)
        continue

    action = parts[0]

    # 检查命令类型以及参数数量是否正确
    if action in {"RESERVE", "RELEASE", "SHIP"}:
        if len(parts) != 4:
            print("REJECTED", on_hand, reserved_total)
            continue

    elif action == "RESTOCK":
        if len(parts) != 3:
            print("REJECTED", on_hand, reserved_total)
            continue

    else:
        # 不属于规定的四种命令
        print("REJECTED", on_hand, reserved_total)
        continue

    event_id = parts[1]

    # event_id 必须是非空 ASCII 字符串
    if not event_id or not event_id.isascii():
        print("REJECTED", on_hand, reserved_total)
        continue

    # 如果这个 event_id 之前已经处理过，
    # 就直接返回 DUPLICATE，不能再次修改库存状态
    if event_id in processed_events:
        print("DUPLICATE", on_hand, reserved_total)
        continue


    # --------------------------------------------------
    # RESERVE：给订单增加预留数量
    # --------------------------------------------------
    if action == "RESERVE":

        order_id = parts[2]

        # order_id 必须是非空 ASCII 字符串
        if not order_id or not order_id.isascii():
            print("REJECTED", on_hand, reserved_total)
            continue

        try:
            qty = int(parts[3])
        except ValueError:
            # 数量无法转换成整数，属于格式错误
            print("REJECTED", on_hand, reserved_total)
            continue

        # 数量必须是 1 到 10^12 之间的正整数
        if qty <= 0 or qty > MAX_QTY:
            print("REJECTED", on_hand, reserved_total)
            continue

        # 计算当前可用库存
        # 可用库存 = 实际库存 - 已预留库存
        available = on_hand - reserved_total

        if qty <= available:

            # 给这个订单增加预留数量
            # 如果订单之前没有预留，就从 0 开始
            reservations[order_id] = (
                reservations.get(order_id, 0) + qty
            )

            # 更新预留总量
            reserved_total += qty

            # 成功处理后记录 event_id
            processed_events.add(event_id)

            print("OK", on_hand, reserved_total)

        else:

            # 业务规则不满足时虽然 REJECTED，
            # 但这个 event_id 仍然算处理过
            processed_events.add(event_id)

            print("REJECTED", on_hand, reserved_total)


    # --------------------------------------------------
    # RELEASE：释放订单已经预留的数量
    # --------------------------------------------------
    elif action == "RELEASE":

        order_id = parts[2]

        # order_id 必须是非空 ASCII 字符串
        if not order_id or not order_id.isascii():
            print("REJECTED", on_hand, reserved_total)
            continue

        try:
            qty = int(parts[3])
        except ValueError:
            # 数量无法转换成整数，属于格式错误
            print("REJECTED", on_hand, reserved_total)
            continue

        # 数量必须是正整数，且不能超过题目规定的最大值
        if qty <= 0 or qty > MAX_QTY:
            print("REJECTED", on_hand, reserved_total)
            continue

        # 获取这个订单当前已经预留的数量
        # 如果订单不存在，就当作预留数量为 0
        current_qty = reservations.get(order_id, 0)

        if qty <= current_qty:

            if qty == current_qty:
                # 如果全部释放，就把这个订单从字典中删除
                del reservations[order_id]
            else:
                # 否则只减少一部分预留数量
                reservations[order_id] = current_qty - qty

            # 更新预留总量
            reserved_total -= qty

            # 记录已经处理过的 event_id
            processed_events.add(event_id)

            print("OK", on_hand, reserved_total)

        else:

            # 释放数量超过当前预留数量，业务规则不允许
            processed_events.add(event_id)

            print("REJECTED", on_hand, reserved_total)


    # --------------------------------------------------
    # SHIP：发货，实际库存和订单预留同时减少
    # --------------------------------------------------
    elif action == "SHIP":

        order_id = parts[2]

        # order_id 必须是非空 ASCII 字符串
        if not order_id or not order_id.isascii():
            print("REJECTED", on_hand, reserved_total)
            continue

        try:
            qty = int(parts[3])
        except ValueError:
            # 数量无法转换成整数，属于格式错误
            print("REJECTED", on_hand, reserved_total)
            continue

        # 数量必须是正整数，且不能超过题目规定的最大值
        if qty <= 0 or qty > MAX_QTY:
            print("REJECTED", on_hand, reserved_total)
            continue

        # 获取这个订单当前的预留数量
        current_qty = reservations.get(order_id, 0)

        if qty <= current_qty:

            if qty == current_qty:
                # 如果这个订单的预留全部发货，就删除订单
                del reservations[order_id]
            else:
                # 否则只减少已经发货的那部分
                reservations[order_id] = current_qty - qty

            # 发货后，订单预留数量减少
            reserved_total -= qty

            # 发货后，仓库实际库存也减少
            on_hand -= qty

            # 记录已经处理过的 event_id
            processed_events.add(event_id)

            print("OK", on_hand, reserved_total)

        else:

            # 发货数量超过订单当前预留数量，业务规则不允许
            processed_events.add(event_id)

            print("REJECTED", on_hand, reserved_total)


    # --------------------------------------------------
    # RESTOCK：仓库补货，只增加实际库存
    # --------------------------------------------------
    elif action == "RESTOCK":

        try:
            qty = int(parts[2])
        except ValueError:
            # 数量无法转换成整数，属于格式错误
            print("REJECTED", on_hand, reserved_total)
            continue

        # 数量必须是正整数，且不能超过题目规定的最大值
        if qty <= 0 or qty > MAX_QTY:
            print("REJECTED", on_hand, reserved_total)
            continue

        # 补货只增加仓库中的实际库存
        # 不会直接增加任何订单的预留数量
        on_hand += qty

        # 记录已经处理过的 event_id
        processed_events.add(event_id)

        print("OK", on_hand, reserved_total)


# 所有命令处理完成后，输出当前仍然存在的开放订单数量
print("OPEN", len(reservations))

# 按照 order_id 的字典序排序后输出开放订单
for order_id in sorted(reservations):
    print(order_id, reservations[order_id])