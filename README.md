# Maze Pathfinding Visualizer

[![Tests](https://github.com/brishabkc24/maze-pathfinding-visualizer/actions/workflows/tests.yml/badge.svg)](https://github.com/brishabkc24/maze-pathfinding-visualizer/actions/workflows/tests.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
[![Download for Windows](https://img.shields.io/github/v/release/brishabkc24/maze-pathfinding-visualizer?label=download%20.exe)](https://github.com/brishabkc24/maze-pathfinding-visualizer/releases/latest)

Watch BFS, DFS, Dijkstra, A\*, Greedy best-first and Hill Climbing solve the
same maze side by side, each in its own colour, with a scoreboard that records
when every one of them started and finished. Made for showing search
algorithms to a class: three numbered steps, plain words everywhere, and a
"How it works" window that explains the rest. Python with Tkinter and nothing
else: no numpy, no pip install, just `python app.py`.

![All six algorithms after a race on maze 21, Maze with some loops](docs/race.png)

## Three steps

1. **Choose a maze.** 26 numbered mazes, each built to make a point: Empty
   room, Wall with a door at the top, The trap, Spiral, Dead ends, Big detour,
   Sealed goal, Classic maze, Maze with some loops, Heavy rubble and more. The
   note under the list says what to look for. Or press *Make a random maze*
   and set how many loops it should have.
2. **Choose the algorithms.** Tick any of the six, or use a quick pick such as
   *BFS vs DFS* or *Dijkstra vs A\**. Each algorithm gets its own panel; fewer
   panels means bigger cells.
3. **Run the race.** Start, Pause, Step one move at a time, Finish now, Reset,
   and a speed slider. Every algorithm moves the same number of steps per tick,
   so the comparison is fair.

Before a race you can draw your own walls: left-drag paints, right-drag
erases, and the green start and red goal dots can be dragged.

The scoreboard lists, for each algorithm, the result, cells checked, path
length, whether that path was the shortest, the clock time it started and
finished, the time taken, and the compute time spent inside the algorithm
alone. A summary line names the shortest path, the fewest cells checked and
the first to finish. *Big text* enlarges everything for a projector, and
*How it works* opens a page that explains the colours, each algorithm and the
scoreboard columns.

## What the race shows

On maze 21, *Maze with some loops* (41×25, 15 % of its inner walls removed),
one run gave:

| Algorithm | Result | Cells checked | Path length | Shortest path? |
| --- | --- | ---: | ---: | --- |
| BFS | path found | 507 | 66 | yes |
| DFS | path found | 142 | 130 | no, 64 longer |
| Dijkstra | path found | 507 | 66 | yes |
| A\* | path found | 248 | 66 | yes |
| Greedy | path found | 81 | 70 | no, 4 longer |
| Hill Climbing | stuck at a local minimum | 23 | | |

BFS and Dijkstra flood half the maze but are always optimal. DFS is quick and
takes twice the path. A\* matches the BFS length while checking half as many
cells. Greedy checks the fewest cells and pays for it with a slightly longer
path. Hill Climbing, which has no memory of where else it could go, walks
until a wall is between it and the goal and stops there.

## Run it

**Windows, no Python needed:** download `MazePathfindingVisualizer.exe` from
the [latest release](https://github.com/brishabkc24/maze-pathfinding-visualizer/releases/latest)
and double-click it. The first launch takes a few seconds while Windows unpacks
it, and SmartScreen may warn because the file is not signed: choose "More
info", then "Run anyway".

**From source:** Python 3.10 or newer with Tkinter (included with the standard
installers on Windows and macOS; on Debian/Ubuntu install `python3-tk`). No
other dependencies.

```bash
git clone https://github.com/brishabkc24/maze-pathfinding-visualizer.git
cd maze-pathfinding-visualizer
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
