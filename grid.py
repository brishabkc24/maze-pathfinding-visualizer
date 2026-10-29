"""The Maze Race grid: a rectangle of open and wall cells plus a start and a goal.

Cells are addressed as ``(row, col)`` tuples. The model knows nothing about
Tkinter; the editor and the pathfinding algorithms both work on it.
"""
from __future__ import annotations

OPEN = 0
WALL = 1

Node = tuple[int, int]

# Up, right, down, left. The order is fixed so that DFS is reproducible.
_STEPS = ((-1, 0), (0, 1), (1, 0), (0, -1))


class Grid:
    """A ``rows`` by ``cols`` field of cells, all open to begin with."""

    def __init__(self, cols: int = 41, rows: int = 25,
                 start: Node | None = None, goal: Node | None = None):
        if cols < 2 or rows < 2:
            raise ValueError("a grid needs at least 2 columns and 2 rows")
        self.cols = cols
        self.rows = rows
        self.cells: list[list[int]] = [[OPEN] * cols for _ in range(rows)]
        self.start: Node = start if start is not None else (min(1, rows - 1), min(1, cols - 1))
        self.goal: Node = goal if goal is not None else (max(rows - 2, 0), max(cols - 2, 0))
        for name, node in (("start", self.start), ("goal", self.goal)):
            if not self.in_bounds(*node):
                raise ValueError(f"{name} {node} is outside the grid")
        if self.start == self.goal:
            raise ValueError("start and goal must be different cells")

    # -- construction helpers -------------------------------------------------

    @classmethod
    def from_rows(cls, rows: list[str]) -> "Grid":
        """Build a grid from strings: ``#`` wall, ``.`` open, ``S`` start, ``G`` goal."""
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError("rows must be non-empty and all the same length")
        start = goal = None
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch == "S":
                    start = (r, c)
                elif ch == "G":
                    goal = (r, c)
        if start is None or goal is None:
            raise ValueError("rows must contain one S and one G")
        grid = cls(len(rows[0]), len(rows), start, goal)
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch == "#":
                    grid.cells[r][c] = WALL
        return grid

    def to_rows(self) -> list[str]:
        """The inverse of :meth:`from_rows`; handy in tests and debugging."""
        out = []
        for r in range(self.rows):
            line = []
            for c in range(self.cols):
                if (r, c) == self.start:
                    line.append("S")
                elif (r, c) == self.goal:
                    line.append("G")
                else:
                    line.append("#" if self.cells[r][c] == WALL else ".")
            out.append("".join(line))
        return out

    def copy(self) -> "Grid":
        clone = Grid(self.cols, self.rows, self.start, self.goal)
        clone.cells = [row[:] for row in self.cells]
        return clone

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Grid):
            return NotImplemented
        return (self.cells == other.cells and self.start == other.start
                and self.goal == other.goal)

    # -- queries ----------------------------------------------------------------

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_open(self, r: int, c: int) -> bool:
        """True for an in-bounds cell that is not a wall."""
        return self.in_bounds(r, c) and self.cells[r][c] == OPEN

    def is_wall(self, r: int, c: int) -> bool:
        return self.in_bounds(r, c) and self.cells[r][c] == WALL

    def neighbors(self, node: Node) -> list[Node]:
        """Open 4-connected neighbours of ``node`` in up, right, down, left order."""
        r, c = node
        return [(r + dr, c + dc) for dr, dc in _STEPS if self.is_open(r + dr, c + dc)]

    @property
    def wall_count(self) -> int:
        return sum(row.count(WALL) for row in self.cells)

    def reachable_from(self, node: Node) -> set[Node]:
        """Every open cell connected to ``node`` through open cells (flood fill)."""
        if not self.is_open(*node):
            return set()
        seen = {node}
        stack = [node]
        while stack:
            for nb in self.neighbors(stack.pop()):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        return seen

    # -- edits (each returns True when something changed) ---------------------

    def set_wall(self, r: int, c: int) -> bool:
        """Turn a cell into a wall. Start and goal cells are never walled."""
        if not self.in_bounds(r, c) or (r, c) in (self.start, self.goal):
            return False
        if self.cells[r][c] == WALL:
            return False
        self.cells[r][c] = WALL
        return True

    def clear_wall(self, r: int, c: int) -> bool:
        if not self.is_wall(r, c):
            return False
        self.cells[r][c] = OPEN
        return True

    def clear_walls(self) -> None:
        for row in self.cells:
            row[:] = [OPEN] * self.cols

    def move_start(self, r: int, c: int) -> bool:
        """Move the start to ``(r, c)``, clearing any wall there."""
        return self._move_endpoint("start", r, c)

    def move_goal(self, r: int, c: int) -> bool:
        """Move the goal to ``(r, c)``, clearing any wall there."""
        return self._move_endpoint("goal", r, c)

    def _move_endpoint(self, which: str, r: int, c: int) -> bool:
        other = self.goal if which == "start" else self.start
        current = getattr(self, which)
        if not self.in_bounds(r, c) or (r, c) == other or (r, c) == current:
            return False
        self.cells[r][c] = OPEN
        setattr(self, which, (r, c))
        return True
