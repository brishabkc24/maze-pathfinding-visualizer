"""The lockstep race.

A :class:`Race` holds one :class:`Runner` per chosen algorithm. Each call to
:meth:`Race.step` advances every unfinished runner by the same number of
events, so the panels stay synchronized, and records for each runner what it
explored, the path it found, when it started and finished, and how much time
it spent inside the algorithm itself.

The race has one clock, started by :meth:`Race.start` and frozen by
:meth:`Race.pause`, so time spent paused never counts as time taken.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterator

from algorithms import Event, Heuristic, bfs, create, manhattan, run
from grid import Grid, Node


@dataclass
class Runner:
    name: str
    color: str
    gen: Iterator[Event]
    clock: Callable[[], float] = lambda: 0.0     # the race clock, set by Race
    explored: set[Node] = field(default_factory=set)
    frontier: set[Node] = field(default_factory=set)
    path: list[Node] | None = None
    done: bool = False
    steps: int = 0
    compute_seconds: float = 0.0
    race_seconds: float | None = None            # race clock when it finished
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def apply(self, event: Event) -> None:
        kind, payload = event
        if kind == "discover":
            if payload not in self.explored:
                self.frontier.add(payload)  # type: ignore[arg-type]
        elif kind == "visit":
            self.frontier.discard(payload)  # type: ignore[arg-type]
            self.explored.add(payload)  # type: ignore[arg-type]
        elif kind == "done":
            self.done = True
            self.path = payload  # type: ignore[assignment]
            self.finished_at = datetime.now()
            self.race_seconds = self.clock()

    @property
    def found(self) -> bool:
        return self.path is not None

    @property
    def path_length(self) -> int | None:
        """Steps from start to goal, or None when no path was found."""
        return None if self.path is None else len(self.path) - 1

    def elapsed(self) -> float:
        """Race-clock seconds from Start to this runner's finish, or to now.
        Time spent paused does not count."""
        if self.race_seconds is not None:
            return self.race_seconds
        return self.clock()

    @property
    def status(self) -> str:
        if not self.done:
            return "running" if self.started_at else "ready"
        return "path found" if self.found else "no path"


class Race:
    """Runs the chosen algorithms on one grid in lockstep."""

    def __init__(self, grid: Grid, entries: list[tuple[str, str]],
                 heuristic: Heuristic = manhattan):
        """``entries`` pairs an algorithm name from :data:`algorithms.ALGORITHMS`
        with a colour; ``heuristic`` is the guess to the goal handed to A*,
        Greedy and Hill Climbing."""
        self.grid = grid
        self.heuristic = heuristic
        self.runners = [Runner(name, color, create(name, grid, heuristic), self.clock)
                        for name, color in entries]
        optimal, _ = run(bfs, grid)
        self.optimal_length: int | None = None if optimal is None else len(optimal) - 1
        self.started_at: datetime | None = None
        self._start_perf: float | None = None
        self._paused_at: float | None = None
        self._paused_total = 0.0

    # -- the clock ----------------------------------------------------------------------

    def start(self) -> None:
        self.started_at = datetime.now()
        self._start_perf = time.perf_counter()
        for runner in self.runners:
            runner.started_at = self.started_at

    @property
    def paused(self) -> bool:
        return self._paused_at is not None

    def pause(self) -> None:
        """Freeze the race clock. Steps taken while paused cost no race time."""
        if self._start_perf is not None and self._paused_at is None:
            self._paused_at = time.perf_counter()

    def resume(self) -> None:
        if self._paused_at is not None:
            self._paused_total += time.perf_counter() - self._paused_at
            self._paused_at = None

    def clock(self) -> float:
        """Seconds of race time so far: since Start, minus every pause."""
        if self._start_perf is None:
            return 0.0
        now = self._paused_at if self._paused_at is not None else time.perf_counter()
        return now - self._start_perf - self._paused_total

    # -- running ---------------------------------------------------------------------------

    def step(self, k: int = 1) -> list[tuple[Runner, Event]]:
        """Advance each unfinished runner by up to ``k`` events.

        Starts the clock on the first call. Returns the events in the order
        they happened so a view can paint them.
        """
        if self.started_at is None:
            self.start()
        events: list[tuple[Runner, Event]] = []
        for runner in self.runners:
            if runner.done:
                continue
            for _ in range(k):
                t0 = time.perf_counter()
                try:
                    event = next(runner.gen)
                except StopIteration:
                    event = ("done", None)
                runner.compute_seconds += time.perf_counter() - t0
                runner.steps += 1
                runner.apply(event)
                events.append((runner, event))
                if runner.done:
                    break
        return events

    @property
    def finished(self) -> bool:
        return all(runner.done for runner in self.runners)

    def run_to_completion(self) -> None:
        while not self.finished:
            self.step(10_000)

    def is_optimal(self, runner: Runner) -> bool | None:
        """True/False once the runner has a path; None while running or without one."""
        if runner.path_length is None or self.optimal_length is None:
            return None
        return runner.path_length == self.optimal_length
