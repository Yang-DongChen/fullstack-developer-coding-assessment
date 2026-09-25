import subprocess
import sys
import unittest


class TestInventoryReservationLedger(unittest.TestCase):

    def run_solution(self, input_data):
        """
        运行 A/solution.py，并返回程序输出。
        """
        result = subprocess.run(
            [sys.executable, "A/solution.py"],
            input=input_data,
            text=True,
            capture_output=True
        )

        # 如果程序运行过程中发生 Python 异常，
        # 测试应该直接失败，并把错误显示出来。
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        return result.stdout


    # --------------------------------------------------
    # 1. 官方 Sample
    # --------------------------------------------------
    def test_official_sample(self):
        input_data = """10 6
RESERVE e1 o100 4
RESERVE e2 o200 7
SHIP e3 o100 2
RELEASE e4 o100 2
RESTOCK e5 3
RESERVE e2 o999 1
"""

        expected_output = """OK 10 4
REJECTED 10 4
OK 8 2
OK 8 0
OK 11 0
DUPLICATE 11 0
OPEN 0
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 2. 成功的 event_id 重复
    # --------------------------------------------------
    def test_duplicate_event_id(self):
        input_data = """10 2
RESERVE e1 o100 4
RESERVE e1 o100 4
"""

        expected_output = """OK 10 4
DUPLICATE 10 4
OPEN 1
o100 4
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 3. REJECTED 的 event_id 再次出现
    # --------------------------------------------------
    def test_rejected_event_is_still_processed(self):
        input_data = """10 3
RESERVE e1 o100 8
RESERVE e2 o200 5
RESERVE e2 o999 1
"""

        expected_output = """OK 10 8
REJECTED 10 8
DUPLICATE 10 8
OPEN 1
o100 8
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 4. RESERVE：库存不足
    # --------------------------------------------------
    def test_reserve_insufficient_stock(self):
        input_data = """5 2
RESERVE e1 o100 6
RESERVE e2 o100 5
"""

        expected_output = """REJECTED 5 0
OK 5 5
OPEN 1
o100 5
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 5. RELEASE：释放数量超过当前预留
    # --------------------------------------------------
    def test_release_more_than_reserved(self):
        input_data = """10 2
RESERVE e1 o100 4
RELEASE e2 o100 5
"""

        expected_output = """OK 10 4
REJECTED 10 4
OPEN 1
o100 4
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 6. SHIP：发货数量超过当前预留
    # --------------------------------------------------
    def test_ship_more_than_reserved(self):
        input_data = """10 2
RESERVE e1 o100 4
SHIP e2 o100 5
"""

        expected_output = """OK 10 4
REJECTED 10 4
OPEN 1
o100 4
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 7. SHIP：实际库存和预留数量同时减少
    # --------------------------------------------------
    def test_ship_reduces_on_hand_and_reserved(self):
        input_data = """10 2
RESERVE e1 o100 4
SHIP e2 o100 2
"""

        expected_output = """OK 10 4
OK 8 2
OPEN 1
o100 2
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 8. RESTOCK：只增加实际库存
    # --------------------------------------------------
    def test_restock(self):
        input_data = """10 2
RESERVE e1 o100 4
RESTOCK e2 3
"""

        expected_output = """OK 10 4
OK 13 4
OPEN 1
o100 4
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 9. RELEASE：全部释放后删除订单
    # --------------------------------------------------
    def test_release_all_removes_order(self):
        input_data = """10 2
RESERVE e1 o100 4
RELEASE e2 o100 4
"""

        expected_output = """OK 10 4
OK 10 0
OPEN 0
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 10. 多个订单：OPEN 必须按照 order_id 排序
    # --------------------------------------------------
    def test_open_reservations_are_sorted(self):
        input_data = """10 2
RESERVE e1 o200 3
RESERVE e2 o100 2
"""

        expected_output = """OK 10 3
OK 10 5
OPEN 2
o100 2
o200 3
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 11. 数量不是整数：不能造成部分状态修改
    # --------------------------------------------------
    def test_malformed_quantity_does_not_change_state(self):
        input_data = """10 3
RESERVE e1 o100 4
RESERVE e2 o200 abc
RESERVE e3 o300 6
"""

        expected_output = """OK 10 4
REJECTED 10 4
OK 10 10
OPEN 2
o100 4
o300 6
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 12. 数量为 0 或负数：必须拒绝
    # --------------------------------------------------
    def test_zero_and_negative_quantity(self):
        input_data = """10 3
RESERVE e1 o100 0
RESTOCK e2 -3
RESERVE e3 o100 4
"""

        expected_output = """REJECTED 10 0
REJECTED 10 0
OK 10 4
OPEN 1
o100 4
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 13. 参数数量错误
    # --------------------------------------------------
    def test_malformed_argument_count(self):
        input_data = """10 3
RESERVE e1 o100
RESTOCK e2
RESTOCK e3 3
"""

        expected_output = """REJECTED 10 0
REJECTED 10 0
OK 13 0
OPEN 0
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 14. 未知命令
    # --------------------------------------------------
    def test_unknown_command(self):
        input_data = """10 2
BUY e1 o100 4
RESTOCK e2 3
"""

        expected_output = """REJECTED 10 0
OK 13 0
OPEN 0
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 15. event_id 非 ASCII
    # --------------------------------------------------
    def test_non_ascii_event_id(self):
        input_data = """10 2
RESERVE 事件1 o100 4
RESERVE e2 o100 4
"""

        expected_output = """REJECTED 10 0
OK 10 4
OPEN 1
o100 4
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 16. order_id 非 ASCII
    # --------------------------------------------------
    def test_non_ascii_order_id(self):
        input_data = """10 2
RESERVE e1 订单1 4
RESERVE e2 o100 4
"""

        expected_output = """REJECTED 10 0
OK 10 4
OPEN 1
o100 4
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 17. qty 超过题目规定的最大值
    # --------------------------------------------------
    def test_quantity_above_maximum(self):
        input_data = """10 2
RESERVE e1 o100 1000000000001
RESTOCK e2 3
"""

        expected_output = """REJECTED 10 0
OK 13 0
OPEN 0
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


    # --------------------------------------------------
    # 18. 最大合法数量 10^12
    # --------------------------------------------------
    def test_maximum_valid_quantity(self):
        input_data = """0 2
RESTOCK e1 1000000000000
RESERVE e2 o100 1000000000000
"""

        expected_output = """OK 1000000000000 0
OK 1000000000000 1000000000000
OPEN 1
o100 1000000000000
"""

        output = self.run_solution(input_data)

        self.assertEqual(output, expected_output)


if __name__ == "__main__":
    unittest.main()