"""Ready-made mazes to race on.

Each template has a name, a note on what the race on it shows, and a builder
that returns a fresh :class:`Grid` every time it is called, so edits made in
the app never leak into the next run.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from grid import OPEN, WALL, Grid, Node
from maze_gen import generate, scatter

COLS, ROWS = 41, 25
MID = (12, 1), (12, 39)            # start and goal on the middle row
CORNERS = (1, 1), (23, 39)         # start and goal in opposite corners


@dataclass(frozen=True)
class Template:
    name: str
    note: str
    build: Callable[[], Grid]
    solvable: bool = True


# -- drawing helpers ----------------------------------------------------------------

def _blank(endpoints: tuple[Node, Node] = CORNERS, border: bool = True) -> Grid:
    start, goal = endpoints
    grid = Grid(COLS, ROWS, start, goal)
    if border:
        for c in range(COLS):
            grid.set_wall(0, c)
            grid.set_wall(ROWS - 1, c)
        for r in range(ROWS):
            grid.set_wall(r, 0)
            grid.set_wall(r, COLS - 1)
    return grid


def _filled(endpoints: tuple[Node, Node]) -> Grid:
    """All walls; corridors are carved into it."""
    start, goal = endpoints
    grid = Grid(COLS, ROWS, start, goal)
    for row in grid.cells:
        row[:] = [WALL] * COLS
    return grid


def _hwall(grid: Grid, r: int, c0: int, c1: int, gaps: tuple[int, ...] = ()) -> None:
    for c in range(c0, c1 + 1):
        if c not in gaps:
            grid.set_wall(r, c)


def _vwall(grid: Grid, c: int, r0: int, r1: int, gaps: tuple[int, ...] = ()) -> None:
    for r in range(r0, r1 + 1):
        if r not in gaps:
            grid.set_wall(r, c)


def _carve_h(grid: Grid, r: int, c0: int, c1: int) -> None:
    for c in range(min(c0, c1), max(c0, c1) + 1):
        grid.cells[r][c] = OPEN


def _carve_v(grid: Grid, c: int, r0: int, r1: int) -> None:
    for r in range(min(r0, r1), max(r0, r1) + 1):
        grid.cells[r][c] = OPEN


def _block(grid: Grid, r0: int, c0: int, height: int, width: int) -> None:
    for r in range(r0, r0 + height):
        for c in range(c0, c0 + width):
            grid.set_wall(r, c)


# -- hand-made mazes -----------------------------------------------------------------

def open_field() -> Grid:
    return _blank()


def clear_run() -> Grid:
    grid = _blank()
    # Blocks off the top row and right column, the beeline hill climbing takes.
    for r0, c0 in ((5, 6), (10, 14), (16, 22), (6, 28), (18, 10), (12, 32)):
        _block(grid, r0, c0, 3, 4)
    return grid


def door_at_the_top() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 20, 2, ROWS - 2)          # the only gap is at row 1
    return grid


def bottleneck() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 20, 1, ROWS - 2, gaps=(12,))
    return grid


def two_doors() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 20, 1, ROWS - 2, gaps=(4, 20))
    return grid


def u_trap() -> Grid:
    grid = _blank(((12, 2), (12, 30)))
    _hwall(grid, 6, 22, 36)
    _hwall(grid, 18, 22, 36)
    _vwall(grid, 22, 6, 18)                # the cup opens towards the right
    return grid


def spiral() -> Grid:
    grid = _filled(((1, 1), (12, 20)))
    r, c = 1, 1
    grid.cells[r][c] = OPEN
    top, left, bottom, right = 1, 1, ROWS - 2, COLS - 2
    while left <= right and top <= bottom:
        while c < right:
            c += 1
            grid.cells[r][c] = OPEN
        while r < bottom:
            r += 1
            grid.cells[r][c] = OPEN
        while c > left:
            c -= 1
            grid.cells[r][c] = OPEN
        top += 2
        while r > top:
            r -= 1
            grid.cells[r][c] = OPEN
        left += 2
        bottom -= 2
        right -= 2
    grid.goal = (r, c)                     # the centre of the spiral
    return grid


def rings() -> Grid:
    grid = _blank(((1, 1), (12, 20)))
    for k in range(1, 6):
        top, bottom = 2 * k, ROWS - 1 - 2 * k
        left, right = 2 * k, COLS - 1 - 2 * k
        gap_row = top if k % 2 else bottom
        _hwall(grid, top, left, right, gaps=(20,) if gap_row == top else ())
        _hwall(grid, bottom, left, right, gaps=(20,) if gap_row == bottom else ())
        _vwall(grid, left, top, bottom)
        _vwall(grid, right, top, bottom)
    return grid


def pillars() -> Grid:
    grid = _blank()
    for r in range(2, ROWS - 1, 2):
        for c in range(2, COLS - 1, 2):
            grid.set_wall(r, c)
    return grid


def rooms_and_doors() -> Grid:
    grid = _blank()
    _vwall(grid, 13, 1, ROWS - 2, gaps=(5, 19))
    _vwall(grid, 27, 1, ROWS - 2, gaps=(7, 17))
    _hwall(grid, 12, 1, COLS - 2, gaps=(6, 20, 34))
    return grid


def serpentine() -> Grid:
    grid = _blank(((1, 1), (23, 1)))
    for i, r in enumerate(range(2, ROWS - 1, 2)):
        gap = COLS - 2 if i % 2 == 0 else 1   # one-cell lanes, doors alternate sides
        _hwall(grid, r, 1, COLS - 2, gaps=(gap,))
    return grid


def dfs_trap() -> Grid:
    grid = _filled(MID)
    _carve_h(grid, 12, 1, COLS - 2)
    for c in range(3, COLS - 2, 2):
        _carve_v(grid, c, 1, ROWS - 2)     # dead-end teeth above and below
    return grid


def diagonal_barrier() -> Grid:
    grid = _blank()
    for i in range(ROWS):
        if i in (4, 20):
            continue                       # two gaps
        grid.set_wall(i, 24 - i)
        grid.set_wall(i, 25 - i)
    return grid


def long_way_around() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 12, 1, ROWS - 3)          # gap at the bottom
    _vwall(grid, 28, 2, ROWS - 2)          # gap at the top
    return grid


def cross() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 20, 4, 20)
    _hwall(grid, 12, 8, 32)
    return grid


def no_exit() -> Grid:
    grid = _blank()
    for r, c in ((22, 38), (22, 39), (23, 38)):
        grid.set_wall(r, c)
    return grid


def islands(seed: int = 11) -> Grid:
    for attempt in range(100):
        rng = random.Random(seed * 10_000 + attempt)
        grid = _blank()
        for _ in range(14):
            height, width = rng.randint(2, 5), rng.randint(2, 7)
            r0 = rng.randint(2, ROWS - 2 - height)
            c0 = rng.randint(2, COLS - 2 - width)
            _block(grid, r0, c0, height, width)
        if grid.goal in grid.reachable_from(grid.start):
            return grid
    raise RuntimeError("could not build a solvable islands maze")


# -- the catalogue -------------------------------------------------------------------

TEMPLATES: list[Template] = [
    Template("Open field",
             "No walls. Every algorithm finds a 60-step path; the difference is how many cells each one touches.",
             open_field),
    Template("Clear run",
             "A few blocks off the direct route. The beeline of hill climbing works here; on most mazes it will not.",
             clear_run),
    Template("Door at the top",
             "The only way through is far from the straight line. Greedy and hill climbing head straight into the wall.",
             door_at_the_top),
    Template("Bottleneck",
             "Two halls joined by one cell. BFS and Dijkstra fill the first hall; A* aims for the gap.",
             bottleneck),
    Template("Two doors",
             "Two equally long routes. Tie-breaking decides which door each algorithm takes; hill climbing takes neither.",
             two_doors),
    Template("U trap",
             "The goal sits in a cup that opens away from the start. Greedy and hill climbing walk straight into it.",
             u_trap),
    Template("Spiral",
             "One long corridor and no choices: every algorithm walks the same path, so they all tie.",
             spiral),
    Template("Rings",
             "Concentric walls with doors on alternating sides: a long forced route with many near misses for greedy.",
             rings),
    Template("Pillars",
             "Hundreds of equally short routes. See how each algorithm breaks ties.",
             pillars),
    Template("Rooms and doors",
             "Six rooms, seven doors. A* and Dijkstra agree on the length; DFS wanders through extra rooms.",
             rooms_and_doors),
    Template("Serpentine",
             "Twelve one-cell lanes joined end to end: a forced route of 460 steps. Everyone ties, and it takes a while.",
             serpentine),
    Template("DFS trap",
             "A straight corridor lined with dead-end teeth. DFS tries every tooth going up before it moves on.",
             dfs_trap),
    Template("Diagonal barrier",
             "A thick diagonal wall with two gaps. The shortest route and the greedy route disagree.",
             diagonal_barrier),
    Template("Long way around",
             "The direct route is blocked both ways and the real path heads away from the goal twice.",
             long_way_around),
    Template("Cross",
             "A plus-shaped wall between start and goal. Hill climbing stops at the first arm.",
             cross),
    Template("No exit",
             "The goal is sealed off. Complete algorithms explore every cell before giving up; hill climbing quits at once.",
             no_exit, solvable=False),
    Template("Islands",
             "Random rectangular blocks. A good general-purpose race.",
             islands),
    Template("Perfect maze 1",
             "A perfect maze has one route between any two cells, so the paths tie; only the explored counts differ.",
             lambda: generate(seed=1)),
    Template("Perfect maze 2",
             "Another perfect maze. Watch DFS get lucky or unlucky depending on which corridor it dives into first.",
             lambda: generate(seed=2)),
    Template("Braided maze 10%",
             "A perfect maze with 10% of its inner walls removed: a few loops, a few shortcuts.",
             lambda: generate(seed=3, braid_fraction=0.10)),
    Template("Braided maze 15%",
             "The showcase: BFS floods, DFS takes a longer path, A* matches the BFS length with far fewer cells.",
             lambda: generate(seed=4, braid_fraction=0.15)),
    Template("Braided maze 25%",
             "More loops: DFS gets more creative and the lead of A* over Dijkstra grows.",
             lambda: generate(seed=5, braid_fraction=0.25)),
    Template("Braided maze 40%",
             "Nearly a field of pillars: lots of equal routes, little for the heuristic to get wrong.",
             lambda: generate(seed=6, braid_fraction=0.40)),
    Template("Rubble 10%",
             "Random obstacles at 10% density: almost open, with just enough in the way to split the pack.",
             lambda: scatter(density=0.10, seed=7)),
    Template("Rubble 20%",
             "Random obstacles at 20% density.",
             lambda: scatter(density=0.20, seed=8)),
    Template("Rubble 30%",
             "Random obstacles at 30% density: narrow passages everywhere, and traps for the greedy approaches.",
             lambda: scatter(density=0.30, seed=9)),
]

BY_NAME: dict[str, Template] = {t.name: t for t in TEMPLATES}
