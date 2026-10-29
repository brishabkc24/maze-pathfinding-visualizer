import pytest

from algorithms import astar, bfs, dfs, greedy, hill_climbing, run
from templates import BY_NAME, TEMPLATES


def test_there_are_at_least_twenty_templates_with_unique_names():
    assert len(TEMPLATES) >= 20
    assert len({t.name for t in TEMPLATES}) == len(TEMPLATES)
    assert all(t.note for t in TEMPLATES)


def test_names_are_short_and_plain():
    for t in TEMPLATES:
        assert len(t.name) <= 32, t.name
        assert "%" not in t.name and "(" not in t.name, t.name


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.name)
def test_template_builds_a_valid_41_by_25_grid(template):
    grid = template.build()
    assert (grid.cols, grid.rows) == (41, 25)
    assert grid.start != grid.goal
    assert grid.is_open(*grid.start) and grid.is_open(*grid.goal)
    reachable = grid.goal in grid.reachable_from(grid.start)
    assert reachable == template.solvable
    assert (run(bfs, grid)[0] is not None) == template.solvable


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.name)
def test_each_build_is_a_fresh_copy(template):
    first = template.build()
    second = template.build()
    assert first == second
    assert first is not second
    first.set_wall(*first.goal)                 # refused, start/goal are never walls
    first.cells[0][0] ^= 1
    assert first != second


def test_only_the_sealed_goal_is_unsolvable():
    assert [t.name for t in TEMPLATES if not t.solvable] == ["Sealed goal"]


@pytest.mark.parametrize("name", ["Wall with a door at the top", "The trap", "Big detour",
                                  "Plus sign", "Wall with two doors"])
def test_hill_climbing_is_trapped_on_the_trap_mazes(name):
    assert run(hill_climbing, BY_NAME[name].build())[0] is None


@pytest.mark.parametrize("name", ["Empty room", "A few blocks", "Wall with a door in the middle"])
def test_hill_climbing_wins_where_nothing_blocks_the_beeline(name):
    grid = BY_NAME[name].build()
    path, _ = run(hill_climbing, grid)
    assert path is not None
    assert len(path) == len(run(bfs, grid)[0])


@pytest.mark.parametrize("name", ["Spiral", "Snake"])
def test_single_corridor_mazes_make_everyone_tie(name):
    grid = BY_NAME[name].build()
    lengths = {len(run(alg, grid)[0]) for alg in (bfs, dfs, astar, greedy)}
    assert len(lengths) == 1


def test_dead_ends_maze_punishes_dfs_but_not_astar():
    grid = BY_NAME["Dead ends"].build()
    _, dfs_checked = run(dfs, grid)
    _, astar_checked = run(astar, grid)
    assert astar_checked < 50 < dfs_checked
