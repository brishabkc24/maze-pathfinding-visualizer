"""The guess to the goal: the three heuristics and how they reach the algorithms."""
import pytest

from algorithms import (ALGORITHMS, HEURISTICS, INFORMED, astar, bfs, chebyshev, create,
                        dijkstra, euclidean, greedy, hill_climbing, manhattan, run)
from grid import Grid
from maze_gen import generate
from race import Race

SEEDS = range(12)


def braided(seed):
    return generate(seed=seed, braid_fraction=0.2)


def test_the_three_guesses_never_overestimate_on_a_grid():
    goal = (12, 20)
    for node in [(r, c) for r in range(25) for c in range(41)]:
        exact = manhattan(node, goal)          # the true distance when no wall is in the way
        assert chebyshev(node, goal) <= euclidean(node, goal) <= exact + 1e-9


@pytest.mark.parametrize("seed", SEEDS)
def test_astar_stays_optimal_with_every_guess_and_manhattan_checks_the_fewest_cells(seed):
    grid = braided(seed)
    best = len(run(bfs, grid)[0])
    explored = {}
    for name, heuristic in HEURISTICS.items():
        path, visited = run(lambda g, h=heuristic: astar(g, h), grid)
        assert len(path) == best, f"A* with the {name} guess is not optimal"
        explored[name] = visited
    assert explored["Manhattan"] <= explored["Euclidean"]
    assert explored["Manhattan"] <= explored["Chebyshev"]


def test_dijkstra_ignores_the_guess():
    grid = braided(1)
    assert list(dijkstra(grid, chebyshev)) == list(dijkstra(grid, manhattan))


def test_greedy_takes_a_different_route_with_a_different_guess():
    assert any(run(lambda g: greedy(g, euclidean), braided(s))
               != run(lambda g: greedy(g, manhattan), braided(s)) for s in SEEDS)


def test_chebyshev_strands_hill_climbing_on_the_diagonal_of_an_empty_room():
    grid = Grid(11, 11)                       # start and goal lie on one diagonal
    assert run(lambda g: hill_climbing(g, manhattan), grid)[0] is not None
    assert run(lambda g: hill_climbing(g, chebyshev), grid)[0] is None


def test_create_hands_the_guess_to_the_informed_algorithms_only():
    grid = braided(2)
    assert INFORMED == {"Dijkstra", "A*", "Greedy", "Hill Climbing"}
    assert set(ALGORITHMS) - INFORMED == {"BFS", "DFS"}
    for name in ALGORITHMS:
        assert list(create(name, grid, euclidean))[-1][0] == "done"
    assert list(create("BFS", grid, euclidean)) == list(bfs(grid))
    assert list(create("A*", grid, euclidean)) == list(astar(grid, euclidean))
    assert list(create("A*", grid, euclidean)) != list(astar(grid, manhattan))


def test_the_race_passes_the_guess_to_its_runners():
    grid = braided(4)
    entries = [(name, "#000000") for name in ALGORITHMS]
    race = Race(grid, entries, heuristic=euclidean)
    race.run_to_completion()
    by_name = {r.name: r for r in race.runners}
    assert race.heuristic is euclidean
    for name in ("A*", "Greedy", "Hill Climbing"):
        path, visited = run(lambda g, alg=ALGORITHMS[name]: alg(g, euclidean), grid)
        assert by_name[name].path == path
        assert len(by_name[name].explored) == visited
    assert by_name["BFS"].path == run(bfs, grid)[0]
    assert Race(grid, entries).heuristic is manhattan
