import time

from algorithms import ALGORITHMS, run
from maze_gen import generate
from race import Race

ENTRIES = [(name, "#000000") for name in ALGORITHMS]


def test_runners_advance_in_lockstep():
    race = Race(generate(seed=1, braid_fraction=0.15), ENTRIES)
    race.step(5)
    assert all(r.steps == 5 for r in race.runners)
    race.step(7)
    assert all(r.steps == 12 or r.done for r in race.runners)


def test_step_starts_the_clocks_and_reports_events():
    race = Race(generate(seed=1), ENTRIES[:2])
    assert race.started_at is None
    events = race.step(3)
    assert race.started_at is not None
    assert all(r.started_at == race.started_at for r in race.runners)
    assert len(events) == 6
    assert all(kind in {"discover", "visit", "done"} for _, (kind, _) in events)


def test_completed_race_matches_direct_runs_and_records_times():
    grid = generate(seed=4, braid_fraction=0.15)
    race = Race(grid, ENTRIES)
    race.run_to_completion()
    assert race.finished
    for runner in race.runners:
        path, visited = run(ALGORITHMS[runner.name], grid)
        assert runner.path == path
        assert len(runner.explored) == visited
        assert runner.frontier.isdisjoint(runner.explored)
        assert runner.started_at is not None and runner.finished_at is not None
        assert runner.finished_at >= runner.started_at
        assert runner.elapsed() >= 0
        assert runner.compute_seconds > 0
        assert runner.status == ("path found" if path else "no path")


def test_optimality_is_judged_against_bfs():
    grid = generate(seed=4, braid_fraction=0.15)
    race = Race(grid, ENTRIES)
    race.run_to_completion()
    by_name = {r.name: r for r in race.runners}
    assert race.optimal_length == by_name["BFS"].path_length
    assert race.is_optimal(by_name["BFS"]) is True
    assert race.is_optimal(by_name["A*"]) is True
    assert race.is_optimal(by_name["Dijkstra"]) is True
    hill = by_name["Hill Climbing"]
    assert race.is_optimal(hill) is None if hill.path is None else race.is_optimal(hill) is not None


def test_pausing_freezes_the_race_clock():
    race = Race(generate(seed=3), ENTRIES[:2])
    assert race.clock() == 0.0
    race.step(5)
    race.pause()
    frozen = race.clock()
    time.sleep(0.03)
    assert race.clock() == frozen
    assert race.runners[0].elapsed() == frozen
    race.step(5)                              # stepping while paused costs no race time
    assert race.clock() == frozen
    race.resume()
    time.sleep(0.01)
    assert race.clock() > frozen
    race.run_to_completion()
    assert all(frozen <= r.elapsed() <= race.clock() for r in race.runners)


def test_finished_runners_are_left_alone():
    race = Race(generate(seed=2), [("Hill Climbing", "#000"), ("BFS", "#fff")])
    race.run_to_completion()
    steps = [r.steps for r in race.runners]
    assert race.step(10) == []
    assert [r.steps for r in race.runners] == steps
