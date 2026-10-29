import pytest

from algorithms import bfs, hill_climbing, run
from templates import BY_NAME, TEMPLATES


def test_there_are_at_least_twenty_templates_with_unique_names():
    assert len(TEMPLATES) >= 20
    assert len({t.name for t in TEMPLATES}) == len(TEMPLATES)
    assert all(t.note for t in TEMPLATES)


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


def test_only_no_exit_is_unsolvable():
    assert [t.name for t in TEMPLATES if not t.solvable] == ["No exit"]


@pytest.mark.parametrize("name", ["Door at the top", "U trap", "Long way around", "Cross", "Two doors"])
def test_hill_climbing_is_trapped_on_the_trap_mazes(name):
    assert run(hill_climbing, BY_NAME[name].build())[0] is None


@pytest.mark.parametrize("name", ["Open field", "Clear run", "Bottleneck"])
def test_hill_climbing_wins_where_nothing_blocks_the_beeline(name):
    grid = BY_NAME[name].build()
    path, _ = run(hill_climbing, grid)
    assert path is not None
    assert len(path) == len(run(bfs, grid)[0])


def test_single_corridor_mazes_make_everyone_tie():
    from algorithms import astar, dfs, greedy
    for name in ("Spiral", "Serpentine"):
        grid = BY_NAME[name].build()
        lengths = {len(run(alg, grid)[0]) for alg in (bfs, dfs, astar, greedy)}
        assert len(lengths) == 1, name
