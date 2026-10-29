"""The lockstep race.

A :class:`Race` holds one :class:`Runner` per chosen algorithm. Each call to
:meth:`Race.step` advances every unfinished runner by the same number of
events, so the panels stay synchronized, and records for each runner what it
explored, the path it found, when it started and finished, and how much time
it spent inside the algorithm itself.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

from algorithms import ALGORITHMS, Event, bfs, run
from grid import Grid, Node


@dataclass
class Runner:
    name: str
    color: str
    gen: Iterator[Event]
    explored: set[Node] = field(default_factory=set)
    frontier: set[Node] = field(default_factory=set)
    path: list[Node] | None = None
    done: bool = False
    steps: int = 0
    compute_seconds: float = 0.0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    _start_perf: float = 0.0
    _end_perf: float | None = None

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
            self._end_perf = time.perf_counter()

    @property
    def found(self) -> bool:
        return self.path is not None

    @property
    def path_length(self) -> int | None:
        """Steps from start to goal, or None when no path was found."""
        return None if self.path is None else len(self.path) - 1

    def elapsed(self) -> float:
        """Wall-clock seconds from the race start to the finish (or to now)."""
        if self.started_at is None:
            return 0.0
        end = self._end_perf if self._end_perf is not None else time.perf_counter()
        return end - self._start_perf

    @property
    def status(self) -> str:
        if not self.done:
            return "running" if self.started_at else "ready"
        return "path found" if self.found else "no path"


class Race:
    """Runs the chosen algorithms on one grid in lockstep."""

    def __init__(self, grid: Grid, entries: list[tuple[str, str]]):
        """``entries`` pairs an algorithm name from :data:`ALGORITHMS` with a colour."""
        self.grid = grid
        self.runners = [Runner(name, color, ALGORITHMS[name](grid)) for name, color in entries]
        optimal, _ = run(bfs, grid)
        self.optimal_length: int | None = None if optimal is None else len(optimal) - 1
        self.started_at: datetime | None = None

    def start(self) -> None:
        self.started_at = datetime.now()
        perf = time.perf_counter()
        for runner in self.runners:
            runner.started_at = self.started_at
            runner._start_perf = perf

    def step(self, k: int = 1) -> list[tuple[Runner, Event]]:
        """Advance each unfinished runner by up to ``k`` events.

        Starts the clocks on the first call. Returns the events in the order
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
