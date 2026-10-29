"""The search algorithms, written as pure generators.

Every algorithm takes a :class:`grid.Grid` and yields events:

    ("discover", node)   the node was added to the frontier (or looked at)
    ("visit", node)      the node was taken off the frontier and expanded
    ("done", path)       the search ended; ``path`` is the list of nodes from
                         start to goal, or None when no path was found

There is no Tkinter in here. The race runner advances these generators one
event at a time, and the tests run them to completion directly.
"""
from __future__ import annotations

import heapq
import itertools
import math
from collections import deque
from typing import Callable, Iterator

from grid import Grid, Node

Event = tuple[str, object]
Heuristic = Callable[[Node, Node], float]
Algorithm = Callable[[Grid], Iterator[Event]]


# -- heuristics -----------------------------------------------------------------

def manhattan(a: Node, b: Node) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a: Node, b: Node) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def chebyshev(a: Node, b: Node) -> float:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


HEURISTICS: dict[str, Heuristic] = {
    "Manhattan": manhattan,
    "Euclidean": euclidean,
    "Chebyshev": chebyshev,
}


def _reconstruct(parent: dict[Node, Node | None], goal: Node) -> list[Node]:
    path = []
    node: Node | None = goal
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return path


# -- uninformed search ------------------------------------------------------------

def bfs(grid: Grid) -> Iterator[Event]:
    """Breadth-first search: a FIFO queue, so the first time the goal is
    reached it is by a shortest path. Explores in rings around the start."""
    start, goal = grid.start, grid.goal
    parent: dict[Node, Node | None] = {start: None}
    queue = deque([start])
    yield ("discover", start)
    while queue:
        node = queue.popleft()
        yield ("visit", node)
        if node == goal:
            yield ("done", _reconstruct(parent, goal))
            return
        for nb in grid.neighbors(node):
            if nb not in parent:
                parent[nb] = node
                queue.append(nb)
                yield ("discover", nb)
    yield ("done", None)


def dfs(grid: Grid) -> Iterator[Event]:
    """Depth-first search: a LIFO stack, so it dives down one corridor as far
    as it goes before backing up. Complete on a finite grid, but the path it
    finds is whatever it stumbled on first, not the shortest."""
    start, goal = grid.start, grid.goal
    parent: dict[Node, Node | None] = {}
    visited: set[Node] = set()
    stack: list[tuple[Node, Node | None]] = [(start, None)]
    yield ("discover", start)
    while stack:
        node, via = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        parent[node] = via
        yield ("visit", node)
        if node == goal:
            yield ("done", _reconstruct(parent, goal))
            return
        # Reversed so that the first neighbour (up) is popped first.
        for nb in reversed(grid.neighbors(node)):
            if nb not in visited:
                stack.append((nb, node))
                yield ("discover", nb)
    yield ("done", None)


# -- best-first family ------------------------------------------------------------

def _best_first(grid: Grid, g_weight: float, h_weight: float,
                heuristic: Heuristic) -> Iterator[Event]:
    """The shared engine behind Dijkstra, A* and Greedy best-first.

    Pops the frontier node with the lowest ``f = g_weight*g + h_weight*h``:
    (1, 0) is Dijkstra, (1, 1) is A*, (0, 1) is Greedy. Heap entries carry an
    increasing counter so that ties break first-in-first-out and nodes are
    never compared. A closed set is checked on pop; a node found again with a
    better g is pushed again and the stale entry is skipped later (lazy
    deletion).
    """
    start, goal = grid.start, grid.goal
    counter = itertools.count()
    g: dict[Node, int] = {start: 0}
    parent: dict[Node, Node | None] = {start: None}
    closed: set[Node] = set()
    heap = [(h_weight * heuristic(start, goal), next(counter), start)]
    yield ("discover", start)
    while heap:
        _, _, node = heapq.heappop(heap)
        if node in closed:
            continue
        closed.add(node)
        yield ("visit", node)
        if node == goal:
            yield ("done", _reconstruct(parent, goal))
            return
        for nb in grid.neighbors(node):
            if nb in closed:
                continue
            if g_weight == 0 and nb in g:
                continue  # greedy keeps the first parent; f would not change
            ng = g[node] + 1  # unit step cost; weighted terrain would read a cell cost here
            if ng < g.get(nb, math.inf):
                g[nb] = ng
                parent[nb] = node
                f = g_weight * ng + h_weight * heuristic(nb, goal)
                heapq.heappush(heap, (f, next(counter), nb))
                yield ("discover", nb)
    yield ("done", None)


def dijkstra(grid: Grid, heuristic: Heuristic = manhattan) -> Iterator[Event]:
    """Uniform-cost search: expands by distance from the start only. On a grid
    with unit costs it explores the same cells as BFS, just in a different
    order, and is always optimal."""
    return _best_first(grid, 1, 0, heuristic)


def astar(grid: Grid, heuristic: Heuristic = manhattan) -> Iterator[Event]:
    """A*: distance so far plus an admissible estimate to the goal. Optimal,
    and explores far fewer cells than BFS or Dijkstra."""
    return _best_first(grid, 1, 1, heuristic)


def greedy(grid: Grid, heuristic: Heuristic = manhattan) -> Iterator[Event]:
    """Greedy best-first: only the estimate to the goal counts. Fast, but the
    path can be far from optimal; the frontier lets it recover from traps."""
    return _best_first(grid, 0, 1, heuristic)


def hill_climbing(grid: Grid, heuristic: Heuristic = manhattan) -> Iterator[Event]:
    """Steepest-ascent hill climbing: from the current cell, move to the
    unvisited neighbour with the best (lowest) heuristic, and only if it is
    strictly better than where we are. No frontier and no backtracking, so it
    gives up at the first local minimum: a wall in the way of the goal."""
    start, goal = grid.start, grid.goal
    node = start
    path = [start]
    visited = {start}
    yield ("visit", start)
    while node != goal:
        best: Node | None = None
        best_h = heuristic(node, goal)
        for nb in grid.neighbors(node):
            if nb in visited:
                continue
            yield ("discover", nb)
            h = heuristic(nb, goal)
            if h < best_h:
                best, best_h = nb, h
        if best is None:
            yield ("done", None)  # local minimum: every better cell is a wall or seen
            return
        node = best
        visited.add(node)
        path.append(node)
        yield ("visit", node)
    yield ("done", path)


# -- registry -----------------------------------------------------------------------

ALGORITHMS: dict[str, Algorithm] = {
    "BFS": bfs,
    "DFS": dfs,
    "Dijkstra": dijkstra,
    "A*": astar,
    "Greedy": greedy,
    "Hill Climbing": hill_climbing,
}

DESCRIPTIONS: dict[str, str] = {
    "BFS": "Queue. Floods outward in rings; the first path it finds is a shortest one.",
    "DFS": "Stack. Dives down one corridor at a time; finds a path, rarely the shortest.",
    "Dijkstra": "Priority queue on distance so far. Optimal; explores like BFS on unit costs.",
    "A*": "Priority queue on distance so far + estimate to goal. Optimal and focused.",
    "Greedy": "Priority queue on the estimate alone. Fast, not optimal, can be lured into traps.",
    "Hill Climbing": "No queue at all: always step to the neighbour nearest the goal; stuck at any wall.",
}


def run(algorithm: Algorithm, grid: Grid) -> tuple[list[Node] | None, int]:
    """Run an algorithm to completion. Returns ``(path, cells_visited)``."""
    visited = 0
    for kind, payload in algorithm(grid):
        if kind == "visit":
            visited += 1
        elif kind == "done":
            return payload, visited  # type: ignore[return-value]
    raise RuntimeError("algorithm ended without a done event")
