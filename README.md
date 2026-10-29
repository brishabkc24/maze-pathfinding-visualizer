# Maze Race

[![Tests](https://github.com/brishabkc24/maze-race/actions/workflows/tests.yml/badge.svg)](https://github.com/brishabkc24/maze-race/actions/workflows/tests.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

Watch BFS, DFS, Dijkstra and A\* race through the same maze side by side.
A pathfinding visualizer written in Python with Tkinter and nothing else:
no numpy, no pip install, just `python app.py`.

## Why a race?

Reading that "A\* is optimal and explores fewer nodes than BFS" is one thing.
Watching four panels flood the same maze at the same time, in lockstep, is
another. On a 41×25 maze with 15 % of its extra walls knocked down so that
there are several routes, one run told this story:

| Algorithm | Cells explored | Path length | Optimal? |
| --- | ---: | ---: | --- |
| BFS | 463 | 61 | yes |
| DFS | 73 | 71 | **no** |
| Dijkstra | 463 | 61 | yes |
| A\* | **104** | 61 | yes |
| Greedy best-first | 114 | 61 | yes, by luck |

BFS floods everything but is optimal. DFS finishes first and takes a longer
path. A\* finds the same optimal path as BFS while visiting about a quarter of
the cells. Greedy happens to be optimal here; on weighted terrain it stops
being so, which is why weighted terrain is on the roadmap.

A "perfect" maze (exactly one path between any two cells) makes every
algorithm return the same path, so the maze generator *braids* the maze by
removing some interior walls. A braid slider at 0 % makes all algorithms tie,
which is itself a useful thing to see.

## Run it

Python 3.10 or newer with Tkinter (included with the standard installers on
Windows and macOS; on Debian/Ubuntu install `python3-tk`).

```bash
python app.py
```

Current state: the **grid editor**. Left-drag paints walls, right-drag erases
them, and the green (start) and red (goal) dots can be dragged to new cells.

## How it works

- `grid.py` is the model: a list-of-lists of open and wall cells plus the
  start and goal, with no Tkinter in it.
- `app.py` draws one rectangle per cell **once** and only recolors them
  afterwards with `itemconfig`. Nothing is deleted and redrawn, which is what
  keeps a Tkinter canvas smooth under animation.
- Each algorithm will be a plain Python generator that yields `("visit", cell)`
  for every expansion and finally `("done", path)`. A single `after()` loop
  advances every live generator by the same number of steps per tick, so the
  panels stay synchronized and the algorithms contain no UI code and are
  tested directly with pytest.

## Roadmap

- [x] Grid editor: paint and erase walls, drag start and goal
- [ ] BFS with the animation loop
- [ ] Race mode: four panels, lockstep runner, live counters
- [ ] Dijkstra, A\* and Greedy through one shared best-first engine, plus a scoreboard
- [ ] Maze generator (recursive backtracker) with a braid slider
- [ ] Heuristic weight slider (0 = Dijkstra, 1 = A\*, 2+ = greedy) and Manhattan / Euclidean / Chebyshev heuristics
- [ ] Weighted terrain (mud cells) to show BFS ignoring costs and Greedy going wrong
- [ ] Step mode and stats polish
- [ ] Demo GIF, About box, v1.0

## Tests

```bash
python -m pytest
```

## License

[MIT](LICENSE)
