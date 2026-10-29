"""Ready-made mazes to race on.

Each template has a short name, a note in plain words on what the race on it
shows, and a builder that returns a fresh :class:`Grid` every time it is
called, so edits made in the app never leak into the next run.
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

def empty_room() -> Grid:
    return _blank()


def a_few_blocks() -> Grid:
    grid = _blank()
    # Blocks off the top row and right column, the beeline hill climbing takes.
    for r0, c0 in ((5, 6), (10, 14), (16, 22), (6, 28), (18, 10), (12, 32)):
        _block(grid, r0, c0, 3, 4)
    return grid


def door_at_the_top() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 20, 2, ROWS - 2)          # the only gap is at row 1
    return grid


def door_in_the_middle() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 20, 1, ROWS - 2, gaps=(12,))
    return grid


def two_doors() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 20, 1, ROWS - 2, gaps=(4, 20))
    return grid


def the_trap() -> Grid:
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


def six_rooms() -> Grid:
    grid = _blank()
    _vwall(grid, 13, 1, ROWS - 2, gaps=(5, 19))
    _vwall(grid, 27, 1, ROWS - 2, gaps=(7, 17))
    _hwall(grid, 12, 1, COLS - 2, gaps=(6, 20, 34))
    return grid


def snake() -> Grid:
    grid = _blank(((1, 1), (23, 1)))
    for i, r in enumerate(range(2, ROWS - 1, 2)):
        gap = COLS - 2 if i % 2 == 0 else 1   # one-cell lanes, doors alternate sides
        _hwall(grid, r, 1, COLS - 2, gaps=(gap,))
    return grid


def dead_ends() -> Grid:
    grid = _filled(MID)
    _carve_h(grid, 12, 1, COLS - 2)
    for c in range(3, COLS - 2, 2):
        _carve_v(grid, c, 1, ROWS - 2)     # dead-end teeth above and below
    return grid


def diagonal_wall() -> Grid:
    grid = _blank()
    for i in range(ROWS):
        if i in (4, 20):
            continue                       # two gaps
        grid.set_wall(i, 24 - i)
        grid.set_wall(i, 25 - i)
    return grid


def big_detour() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 12, 1, ROWS - 3)          # gap at the bottom
    _vwall(grid, 28, 2, ROWS - 2)          # gap at the top
    return grid


def plus_sign() -> Grid:
    grid = _blank(MID)
    _vwall(grid, 20, 4, 20)
    _hwall(grid, 12, 8, 32)
    return grid


def sealed_goal() -> Grid:
    grid = _blank()
    for r, c in ((22, 38), (22, 39), (23, 38)):
        grid.set_wall(r, c)
    return grid


def random_blocks(seed: int = 11) -> Grid:
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
    raise RuntimeError("could not build a solvable random-blocks maze")


# -- the catalogue -------------------------------------------------------------------

TEMPLATES: list[Template] = [
    Template("Empty room",
             "No walls at all. Everyone finds a 60-step path. Compare how many cells each one checks to get there.",
             empty_room),
    Template("A few blocks",
             "Some blocks, but nothing on the straight route. Even hill climbing gets through here.",
             a_few_blocks),
    Template("Wall with a door at the top",
             "The only door is far from the straight line. Greedy and hill climbing run straight into the wall.",
             door_at_the_top),
    Template("Wall with a door in the middle",
             "One door, right on the straight line. BFS and Dijkstra fill the whole left half before they find it.",
             door_in_the_middle),
    Template("Wall with two doors",
             "Two doors, both giving the same path length. Watch which door each algorithm picks.",
             two_doors),
    Template("The trap",
             "The goal sits inside a cup that opens on the far side. Greedy and hill climbing walk straight into it.",
             the_trap),
    Template("Spiral",
             "One long corridor with no choices. Every algorithm walks the same path, so they all tie.",
             spiral),
    Template("Rings",
             "Walls in rings, each with one door, on alternating sides. A long route with lots of near misses.",
             rings),
    Template("Pillars",
             "Hundreds of shortest paths, all the same length. See how each algorithm chooses between them.",
             pillars),
    Template("Six rooms",
             "Rooms joined by doors. DFS wanders through extra rooms; A* goes from door to door.",
             six_rooms),
    Template("Snake",
             "Twelve lanes joined end to end: one forced route of 460 steps. Everyone ties, and it takes a while.",
             snake),
    Template("Dead ends",
             "A straight corridor with dead ends on both sides. DFS tries every dead end going up before it moves on.",
             dead_ends),
    Template("Diagonal wall",
             "A thick diagonal wall with two gaps. The shortest route and the greedy route disagree.",
             diagonal_wall),
    Template("Big detour",
             "The straight route is blocked twice. The real path moves away from the goal, which greedy hates.",
             big_detour),
    Template("Plus sign",
             "A plus-shaped wall in the middle. Hill climbing stops at the first arm it meets.",
             plus_sign),
    Template("Sealed goal",
             "There is no way in. The complete algorithms check every cell before giving up; hill climbing gives up at once.",
             sealed_goal, solvable=False),
    Template("Random blocks",
             "Random rectangles. A good all-round race.",
             random_blocks),
    Template("Classic maze A",
             "A proper maze with exactly one route between any two cells. The paths tie; only the cells checked differ.",
             lambda: generate(seed=1)),
    Template("Classic maze B",
             "Another classic maze. DFS gets lucky or unlucky depending on which corridor it tries first.",
             lambda: generate(seed=2)),
    Template("Maze with a few loops",
             "A classic maze with 10% of its inner walls removed, so there are a few shortcuts.",
             lambda: generate(seed=3, braid_fraction=0.10)),
    Template("Maze with some loops",
             "The showcase: BFS floods, DFS takes a long path, A* finds the shortest with far fewer cells checked.",
             lambda: generate(seed=4, braid_fraction=0.15)),
    Template("Maze with many loops",
             "More loops: DFS gets more creative and A* pulls further ahead of Dijkstra.",
             lambda: generate(seed=5, braid_fraction=0.25)),
    Template("Maze with lots of loops",
             "Almost a field of pillars: lots of equal routes, little for the heuristic to get wrong.",
             lambda: generate(seed=6, braid_fraction=0.40)),
    Template("Light rubble",
             "Random rocks covering 10% of the floor: almost open, with just enough in the way to split the pack.",
             lambda: scatter(density=0.10, seed=7)),
    Template("Medium rubble",
             "Random rocks covering 20% of the floor.",
             lambda: scatter(density=0.20, seed=8)),
    Template("Heavy rubble",
             "Random rocks covering 30% of the floor: narrow passages everywhere, and traps for the greedy ones.",
             lambda: scatter(density=0.30, seed=9)),
]

BY_NAME: dict[str, Template] = {t.name: t for t in TEMPLATES}
