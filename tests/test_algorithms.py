import pytest

from algorithms import (ALGORITHMS, astar, bfs, dfs, dijkstra, greedy,
                        hill_climbing, manhattan, run)
from grid import Grid
from maze_gen import generate

SEEDS = range(12)
OPTIMAL = (bfs, dijkstra, astar)


def braided(seed):
    return generate(seed=seed, braid_fraction=0.2)


def assert_valid_path(grid, path):
    assert path[0] == grid.start
    assert path[-1] == grid.goal
    for a, b in zip(path, path[1:]):
        assert manhattan(a, b) == 1, f"{a} -> {b} is not one step"
    assert all(grid.is_open(*node) for node in path)
    assert len(set(path)) == len(path), "a path never revisits a cell"


@pytest.mark.parametrize("seed", SEEDS)
def test_bfs_dijkstra_and_astar_agree_on_the_optimal_length(seed):
    grid = braided(seed)
    lengths = {len(run(alg, grid)[0]) for alg in OPTIMAL}
    assert len(lengths) == 1


@pytest.mark.parametrize("seed", SEEDS)
def test_every_path_found_is_contiguous_open_and_ends_at_the_goal(seed):
    grid = braided(seed)
    for name, alg in ALGORITHMS.items():
        path, _ = run(alg, grid)
        if path is None:
            assert name == "Hill Climbing", f"{name} must find a path on a connected maze"
        else:
            assert_valid_path(grid, path)


@pytest.mark.parametrize("seed", SEEDS)
def test_dfs_and_greedy_are_never_shorter_than_bfs(seed):
    grid = braided(seed)
    best = len(run(bfs, grid)[0])
    assert len(run(dfs, grid)[0]) >= best
    assert len(run(greedy, grid)[0]) >= best


@pytest.mark.parametrize("seed", SEEDS)
def test_astar_explores_no_more_than_dijkstra(seed):
    grid = braided(seed)
    assert run(astar, grid)[1] <= run(dijkstra, grid)[1]


def test_dfs_is_suboptimal_somewhere():
    """The point of the race: DFS finds a path but usually not the shortest."""
    assert any(len(run(dfs, braided(s))[0]) > len(run(bfs, braided(s))[0]) for s in SEEDS)


def test_hill_climbing_walks_a_beeline_on_an_open_grid():
    grid = Grid(11, 11)
    path, visited = run(hill_climbing, grid)
    assert_valid_path(grid, path)
    assert len(path) - 1 == manhattan(grid.start, grid.goal)
    assert visited == len(path)


def test_hill_climbing_gets_stuck_at_a_wall_between_it_and_the_goal():
    grid = Grid.from_rows([
        ".......",
        ".......",
        "S..#..G",
        ".......",
        ".......",
    ])
    assert run(hill_climbing, grid)[0] is None
    assert run(bfs, grid)[0] is not None


def test_every_algorithm_reports_no_path_when_the_goal_is_sealed():
    grid = Grid.from_rows([
        "S....",
        ".....",
        "...##",
        "...#G",
    ])
    for alg in ALGORITHMS.values():
        assert run(alg, grid)[0] is None


def test_complete_algorithms_explore_everything_reachable_before_giving_up():
    grid = Grid.from_rows([
        "S....",
        ".....",
        "...##",
        "...#G",
    ])
    reachable = len(grid.reachable_from(grid.start))
    for alg in (bfs, dfs, dijkstra, astar, greedy):
        assert run(alg, grid)[1] == reachable


def test_event_stream_is_well_formed():
    grid = braided(3)
    for alg in ALGORITHMS.values():
        events = list(alg(grid))
        kinds = [kind for kind, _ in events]
        assert set(kinds) <= {"discover", "visit", "done"}
        assert kinds[-1] == "done" and kinds.count("done") == 1
        visits = [node for kind, node in events if kind == "visit"]
        assert len(visits) == len(set(visits)), "a cell is expanded at most once"
        assert visits[0] == grid.start


def test_algorithms_leave_the_grid_untouched():
    grid = braided(5)
    before = grid.copy()
    for alg in ALGORITHMS.values():
        run(alg, grid)
    assert grid == before


def test_registry_lists_the_six_racers():
    assert list(ALGORITHMS) == ["BFS", "DFS", "Dijkstra", "A*", "Greedy", "Hill Climbing"]
