# Maze Race

[![Tests](https://github.com/brishabkc24/maze-race/actions/workflows/tests.yml/badge.svg)](https://github.com/brishabkc24/maze-race/actions/workflows/tests.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

Watch BFS, DFS, Dijkstra, A\*, Greedy best-first and Hill Climbing race
through the same maze side by side, each in its own colour, with a scoreboard
that records when every one of them started and finished. A pathfinding
visualizer written in Python with Tkinter and nothing else: no numpy, no pip
install, just `python app.py`.

![All six algorithms after a race on the braided showcase maze](docs/race.png)

## What you can do

- **Pick a maze** from 26 ready-made ones, each built to make a point: an
  open field, a door far from the straight line, a U-shaped trap, a spiral,
  a corridor lined with dead ends, a sealed goal, perfect and braided mazes,
  random rubble. The note under the picker says what to look for.
- **Generate a random maze** with the braid slider: 0 % gives a perfect maze
  with one route, so every algorithm finds the same path; more braid means
  more loops and more ways to be wrong.
- **Choose who races.** Tick any of BFS, DFS, Dijkstra, A\*, Greedy and Hill
  Climbing. One panel per algorithm; fewer panels means bigger cells.
- **Edit the maze by hand** before a race: left-drag paints walls, right-drag
  erases, and the green start and red goal dots can be dragged.
- **Run it your way:** Start/Pause, one Step at a time, Finish now, and a
  speed slider. Space, Right arrow, F and Esc do the same from the keyboard.
- **Read the scoreboard:** result, cells explored, path length, whether that
  path was the shortest possible, start time, finish time, race time, and the
  time spent inside the algorithm itself.

## What the race shows

On the showcase maze (41×25, 15 % of its inner walls removed) one run gave:

| Algorithm | Result | Cells explored | Path length | Shortest? |
| --- | --- | ---: | ---: | --- |
| BFS | path found | 507 | 66 | yes |
| DFS | path found | 142 | 130 | no (+64) |
| Dijkstra | path found | 507 | 66 | yes |
| A\* | path found | 248 | 66 | yes |
| Greedy | path found | 81 | 70 | no (+4) |
| Hill Climbing | stuck at a local minimum | 23 | | |

BFS and Dijkstra flood half the maze but are always optimal. DFS is quick and
takes twice the path. A\* matches the BFS length while visiting half as many
cells. Greedy visits the fewest cells and pays for it with a slightly longer
path. Hill Climbing, which has no memory of where else it could go, walks
until a wall is between it and the goal and stops there.

## Run it

Python 3.10 or newer with Tkinter (included with the standard installers on
Windows and macOS; on Debian/Ubuntu install `python3-tk`).

```bash
python app.py
```

## How it works

- `grid.py` is the model: a list-of-lists of open and wall cells plus the
  start and goal, with no Tkinter in it.
- `algorithms.py` holds the six searches as plain Python generators. Each one
  yields `("discover", cell)` when it adds a cell to its frontier,
  `("visit", cell)` when it expands one, and finally `("done", path)`.
  Dijkstra, A\* and Greedy are one best-first engine with different weights
  on distance-so-far and the heuristic. Hill Climbing is steepest ascent with
  no backtracking, which is why it can get stuck.
- `race.py` advances every chosen generator by the same number of events per
  tick, so the panels stay in lockstep, and records for each one the cells
  explored, the path, the clock times it started and finished, and the time
  spent inside the generator.
- `maze_gen.py` carves a perfect maze by recursive backtracking and then
  *braids* it by removing a fraction of the walls between corridors.
  `templates.py` is the catalogue of ready-made mazes.
- `app.py` draws one rectangle per cell **once** per panel and only recolors
  them afterwards. Nothing is deleted and redrawn, which is what keeps the
  canvas smooth with six panels animating at once.

## Tests

```bash
python -m pytest
```

The suite checks, over many seeded mazes, that BFS, Dijkstra and A\* agree on
the shortest length, that every path is contiguous and open, that DFS and
Greedy are never shorter than BFS, that A\* never explores more than
Dijkstra, that the generators leave the grid untouched, that the maze
generator produces a spanning tree and braiding only removes walls, that
every template is solvable (except the one meant not to be), and that the
race runner keeps the algorithms in lockstep and records their times.

## License

[MIT](LICENSE)
