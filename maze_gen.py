"""Maze generation: a perfect maze by recursive backtracking, then braiding.

A perfect maze has exactly one route between any two cells, so every
algorithm that finds a path finds the same one. :func:`braid` knocks down a
fraction of the walls that separate two corridors, creating loops and
alternative routes, which is what makes the race interesting.

Everything here is seedable so the templates are reproducible.
"""
from __future__ import annotations

import random

from grid import OPEN, WALL, Grid


def generate(cols: int = 41, rows: int = 25, seed: int | None = None,
             braid_fraction: float = 0.0) -> Grid:
    """A maze on an odd-sized grid: corridors on odd coordinates, walls between.

    The start is the top-left corridor cell and the goal the bottom-right one.
    """
    cols = max(5, cols | 1)  # force odd
    rows = max(5, rows | 1)
    rng = random.Random(seed)
    grid = Grid(cols, rows, start=(1, 1), goal=(rows - 2, cols - 2))
    for row in grid.cells:
        row[:] = [WALL] * cols

    def carve(r: int, c: int) -> None:
        grid.cells[r][c] = OPEN

    carve(1, 1)
    stack = [(1, 1)]
    while stack:
        r, c = stack[-1]
        options = []
        for dr, dc in ((-2, 0), (0, 2), (2, 0), (0, -2)):
            nr, nc = r + dr, c + dc
            if 0 < nr < rows - 1 and 0 < nc < cols - 1 and grid.cells[nr][nc] == WALL:
                options.append((nr, nc))
        if not options:
            stack.pop()
            continue
        nr, nc = rng.choice(options)
        carve((r + nr) // 2, (c + nc) // 2)
        carve(nr, nc)
        stack.append((nr, nc))

    if braid_fraction > 0:
        braid(grid, braid_fraction, rng)
    return grid


def braid_candidates(grid: Grid) -> list[tuple[int, int]]:
    """Interior walls with open cells on both sides (vertically or horizontally).
    Removing one never isolates anything; it only adds a loop."""
    out = []
    for r in range(1, grid.rows - 1):
        for c in range(1, grid.cols - 1):
            if not grid.is_wall(r, c):
                continue
            if (grid.is_open(r - 1, c) and grid.is_open(r + 1, c)) or \
               (grid.is_open(r, c - 1) and grid.is_open(r, c + 1)):
                out.append((r, c))
    return out


def braid(grid: Grid, fraction: float, rng: random.Random | None = None) -> int:
    """Open ``fraction`` (0 to 1) of the braid candidates. Returns how many walls went."""
    fraction = min(1.0, max(0.0, fraction))
    rng = rng or random.Random()
    candidates = braid_candidates(grid)
    rng.shuffle(candidates)
    count = round(fraction * len(candidates))
    for r, c in candidates[:count]:
        grid.cells[r][c] = OPEN
    return count


def scatter(cols: int = 41, rows: int = 25, density: float = 0.25,
            seed: int = 0, border: bool = True) -> Grid:
    """Random obstacles with the given density, re-rolled until the goal is
    reachable from the start. Deterministic for a given seed."""
    for attempt in range(1000):
        rng = random.Random(seed * 10_000 + attempt)
        grid = Grid(cols, rows)
        for r in range(rows):
            for c in range(cols):
                on_border = r in (0, rows - 1) or c in (0, cols - 1)
                if (border and on_border) or rng.random() < density:
                    grid.set_wall(r, c)
        if grid.goal in grid.reachable_from(grid.start):
            return grid
    raise RuntimeError("could not find a solvable scatter maze")
