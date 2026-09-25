from solution import solve


def test_official_sample():
    text = """\
3 7
AU 5 8 2
CN 7 20 1
US 4 3 4
"""

    assert solve(text) == """\
1 27
CN 7
"""


def test_impossible_order():
    text = """\
2 10
AU 3 5 1
CN 4 6 2
"""

    assert solve(text) == "-1\n"


def test_zero_stock_warehouse():
    text = """\
3 5
AU 0 1 1
CN 5 20 1
US 4 3 4
"""

    assert solve(text) == """\
1 25
CN 5
"""


def test_minimise_warehouse_count_first():
    text = """\
3 5
A 3 0 1
B 2 0 1
C 5 100 1
"""

    assert solve(text) == """\
1 105
C 5
"""


def test_minimise_cost_second():
    text = """\
3 6
A 6 20 3
B 6 5 4
C 6 10 4
"""

    assert solve(text) == """\
1 29
B 6
"""


def test_lexicographical_tie_breaking():
    text = """\
2 3
A 3 10 0
B 3 10 0
"""

    assert solve(text) == """\
1 10
B 3
"""


def test_split_allocation():
    text = """\
3 7
A 3 5 2
B 3 1 2
C 7 30 10
"""

    assert solve(text) == """\
1 100
C 7
"""


def test_large_quantity():
    text = """\
3 2000
A 1000 10 1
B 1000 20 1
C 1000 30 1
"""

    assert solve(text) == """\
2 2030
A 1000
B 1000
"""


def test_unsorted_input():
    text = """\
3 7
US 4 3 4
CN 7 20 1
AU 5 8 2
"""

    assert solve(text) == """\
1 27
CN 7
"""


def test_zero_stock_can_be_ignored():
    text = """\
2 1
A 0 0 0
B 1 7 0
"""

    assert solve(text) == """\
1 7
B 1
"""