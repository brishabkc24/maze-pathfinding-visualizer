import pytest

from grid import OPEN, WALL, Grid


def test_default_grid_is_open_with_endpoints_in_opposite_corners():
    g = Grid()
    assert (g.cols, g.rows) == (41, 25)
    assert g.start == (1, 1)
    assert g.goal == (23, 39)
    assert g.wall_count == 0
    assert all(cell == OPEN for row in g.cells for cell in row)


def test_rejects_degenerate_grids_and_bad_endpoints():
    with pytest.raises(ValueError):
        Grid(1, 5)
    with pytest.raises(ValueError):
        Grid(5, 5, start=(5, 0))
    with pytest.raises(ValueError):
        Grid(5, 5, start=(2, 2), goal=(2, 2))


def test_set_and_clear_wall_report_whether_anything_changed():
    g = Grid(5, 5)
    assert g.set_wall(2, 2) is True
    assert g.is_wall(2, 2)
    assert g.set_wall(2, 2) is False          # already a wall
    assert g.clear_wall(2, 2) is True
    assert g.is_open(2, 2)
    assert g.clear_wall(2, 2) is False        # already open
    assert g.set_wall(9, 9) is False          # out of bounds


def test_start_and_goal_cells_cannot_become_walls():
    g = Grid(5, 5)
    assert g.set_wall(*g.start) is False
    assert g.set_wall(*g.goal) is False
    assert g.wall_count == 0


def test_is_open_is_false_outside_the_grid():
    g = Grid(5, 5)
    assert not g.is_open(-1, 0)
    assert not g.is_open(0, 5)
    assert not g.is_wall(0, 5)
    assert not g.in_bounds(5, 0)


def test_moving_an_endpoint_clears_the_wall_underneath():
    g = Grid(7, 7)
    g.set_wall(3, 3)
    assert g.move_start(3, 3) is True
    assert g.start == (3, 3)
    assert g.is_open(3, 3)
    assert g.move_goal(0, 0) is True
    assert g.goal == (0, 0)


def test_endpoints_cannot_land_on_each_other_or_outside():
    g = Grid(5, 5)
    assert g.move_start(*g.goal) is False
    assert g.move_goal(*g.start) is False
    assert g.move_start(7, 7) is False
    assert g.move_start(*g.start) is False    # no-op move
    assert g.start == (1, 1) and g.goal == (3, 3)


def test_neighbors_are_open_in_bounds_cells_in_fixed_order():
    g = Grid.from_rows([
        "S....",
        ".#...",
        "...#G",
    ])
    assert g.neighbors((0, 0)) == [(0, 1), (1, 0)]            # right, down
    assert g.neighbors((1, 2)) == [(0, 2), (1, 3), (2, 2)]    # up, right, down; left is a wall
    assert g.neighbors((2, 4)) == [(1, 4)]                    # up only


def test_from_rows_and_to_rows_round_trip():
    rows = [
        "S#...",
        ".#.#.",
        "...#G",
    ]
    g = Grid.from_rows(rows)
    assert g.start == (0, 0) and g.goal == (2, 4)
    assert g.wall_count == 4
    assert g.to_rows() == rows


def test_from_rows_validates_its_input():
    with pytest.raises(ValueError):
        Grid.from_rows(["S..", ".G"])          # ragged
    with pytest.raises(ValueError):
        Grid.from_rows(["S..", "..."])         # no goal


def test_clear_walls_keeps_endpoints():
    g = Grid(6, 4)
    g.set_wall(0, 0)
    g.set_wall(3, 5)
    g.clear_walls()
    assert g.wall_count == 0
    assert g.start == (1, 1) and g.goal == (2, 4)


def test_copy_is_independent_and_equality_compares_contents():
    g = Grid(5, 5)
    g.set_wall(2, 2)
    clone = g.copy()
    assert clone == g
    clone.set_wall(0, 4)
    assert clone != g
    assert g.cells[0][4] == OPEN
    clone.clear_wall(0, 4)
    assert clone == g
    assert g.cells[2][2] == WALL


def test_reachable_from_floods_only_through_open_cells():
    g = Grid.from_rows([
        "S.#..",
        "..#.G",
        "#####",
    ])
    assert g.reachable_from(g.start) == {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert g.goal not in g.reachable_from(g.start)
    assert g.reachable_from((2, 2)) == set()      # a wall reaches nothing
