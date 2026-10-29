import random

import pytest

from grid import OPEN, WALL
from maze_gen import braid, braid_candidates, generate, scatter


def open_cells(grid):
    return {(r, c) for r in range(grid.rows) for c in range(grid.cols) if grid.is_open(r, c)}


def open_edges(grid):
    """Pairs of adjacent open cells, each counted once."""
    count = 0
    for r in range(grid.rows):
        for c in range(grid.cols):
            if grid.is_open(r, c):
                count += grid.is_open(r, c + 1) + grid.is_open(r + 1, c)
    return count


@pytest.mark.parametrize("seed", range(10))
def test_perfect_maze_is_a_spanning_tree_of_the_corridor_cells(seed):
    grid = generate(seed=seed)
    cells = open_cells(grid)
    assert grid.reachable_from(grid.start) == cells
    corridors = {(r, c) for r in range(1, grid.rows, 2) for c in range(1, grid.cols, 2)}
    assert corridors <= cells
    assert open_edges(grid) == len(cells) - 1       # connected and acyclic


def test_generate_is_deterministic_for_a_seed_and_varies_across_seeds():
    assert generate(seed=42) == generate(seed=42)
    assert generate(seed=42) != generate(seed=43)


def test_generate_rounds_even_sizes_up_to_odd_and_places_the_endpoints():
    grid = generate(cols=20, rows=10, seed=1)
    assert (grid.cols, grid.rows) == (21, 11)
    assert grid.start == (1, 1) and grid.goal == (9, 19)
    assert grid.is_open(*grid.start) and grid.is_open(*grid.goal)


def test_braid_only_removes_walls_and_reports_how_many():
    grid = generate(seed=7)
    before = grid.copy()
    candidates = len(braid_candidates(grid))
    removed = braid(grid, 0.3, random.Random(1))
    assert removed == round(0.3 * candidates)
    changed = [(r, c) for r in range(grid.rows) for c in range(grid.cols)
               if grid.cells[r][c] != before.cells[r][c]]
    assert len(changed) == removed
    assert all(before.cells[r][c] == WALL and grid.cells[r][c] == OPEN for r, c in changed)
    assert all(0 < r < grid.rows - 1 and 0 < c < grid.cols - 1 for r, c in changed)


def test_braiding_adds_loops_without_disconnecting_anything():
    grid = generate(seed=8, braid_fraction=0.2)
    cells = open_cells(grid)
    assert grid.reachable_from(grid.start) == cells
    assert open_edges(grid) > len(cells) - 1


def test_braid_zero_changes_nothing():
    grid = generate(seed=9)
    before = grid.copy()
    assert braid(grid, 0.0) == 0
    assert grid == before


def test_scatter_is_solvable_and_deterministic():
    a = scatter(density=0.3, seed=5)
    b = scatter(density=0.3, seed=5)
    assert a == b
    assert a.goal in a.reachable_from(a.start)
    assert 0.15 < a.wall_count / (a.cols * a.rows) < 0.5
