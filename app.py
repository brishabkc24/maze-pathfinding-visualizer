"""Maze Race: the Tkinter app.

Pick a maze, tick the algorithms that should race, press Start and watch them
solve the same maze side by side, each in its own colour. The scoreboard
records when each one started and finished, how many cells it explored, the
length of its path and whether that path was the shortest possible.

Run with ``python app.py``.
"""
from __future__ import annotations

import math
import random
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from algorithms import ALGORITHMS, DESCRIPTIONS
from grid import Grid, Node
from maze_gen import generate
from race import Race, Runner
from templates import BY_NAME, TEMPLATES

TICK_MS = 25             # one animation tick; the speed slider sets events per tick
SIDEBAR_WIDTH = 272
DEFAULT_TEMPLATE = "Braided maze 15%"

COLOR_WALL = "#1f2933"
COLOR_OPEN = "#f5f5f0"
COLOR_GRIDLINE = "#e2e0d8"
COLOR_START = "#2e9e4f"
COLOR_GOAL = "#d64545"
COLOR_PATH = "#ffc400"
COLOR_BG = "#e9e7e0"
COLOR_TEXT = "#1f2933"
COLOR_MUTED = "#5b6470"

ALGO_COLORS = {
    "BFS": "#1f6feb",
    "DFS": "#8250df",
    "Dijkstra": "#0d9488",
    "A*": "#e8590c",
    "Greedy": "#d6336c",
    "Hill Climbing": "#4b5563",
}

FONT = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 8)

HINT = ("Before a race: left-drag paints walls, right-drag erases them, "
        "and the green (start) and red (goal) dots can be dragged.\n"
        "Keys: Space start/pause, Right arrow one step, F finish now, Esc reset.")


def blend(color: str, other: str, t: float) -> str:
    """Mix ``color`` towards ``other`` by ``t`` (0 keeps color, 1 gives other)."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def fmt_clock(moment: datetime | None) -> str:
    if moment is None:
        return ""
    return moment.strftime("%H:%M:%S.") + f"{moment.microsecond // 1000:03d}"


class GridCanvas(tk.Canvas):
    """Draws one :class:`Grid`.

    Every cell rectangle is created once, here in ``__init__``. Afterwards
    cells are only recolored with ``itemconfig`` and the start and goal dots
    are moved with ``coords``; nothing is deleted and redrawn. That is what
    keeps a Tkinter canvas smooth while thousands of cells are animated.
    """

    def __init__(self, master: tk.Misc, model: Grid, cell: int, **kwargs):
        super().__init__(master, width=model.cols * cell, height=model.rows * cell,
                         highlightthickness=0, bg=COLOR_OPEN, **kwargs)
        self.model = model
        self.cell = cell
        outline = COLOR_GRIDLINE if cell >= 8 else ""
        self.rects = [
            [self.create_rectangle(c * cell, r * cell, (c + 1) * cell, (r + 1) * cell,
                                   fill=COLOR_OPEN, outline=outline)
             for c in range(model.cols)]
            for r in range(model.rows)
        ]
        self._dot_pad = max(1, cell // 5)
        self.start_dot = self.create_oval(0, 0, 0, 0, fill=COLOR_START, outline="")
        self.goal_dot = self.create_oval(0, 0, 0, 0, fill=COLOR_GOAL, outline="")
        self.redraw()

    def node_at(self, x: int, y: int) -> Node | None:
        """The cell under canvas pixel ``(x, y)``, or None outside the grid."""
        r, c = y // self.cell, x // self.cell
        return (r, c) if self.model.in_bounds(r, c) else None

    def paint_cell(self, node: Node, color: str | None = None) -> None:
        """Recolor one cell; by default from the model (wall or open)."""
        r, c = node
        if color is None:
            color = COLOR_WALL if self.model.is_wall(r, c) else COLOR_OPEN
        self.itemconfig(self.rects[r][c], fill=color)

    def place_dots(self) -> None:
        self._place(self.start_dot, self.model.start)
        self._place(self.goal_dot, self.model.goal)

    def _place(self, item: int, node: Node) -> None:
        r, c = node
        pad, size = self._dot_pad, self.cell
        self.coords(item, c * size + pad, r * size + pad,
                    (c + 1) * size - pad, (r + 1) * size - pad)

    def redraw(self) -> None:
        """Repaint every cell from the model. For bulk changes only."""
        for r in range(self.model.rows):
            for c in range(self.model.cols):
                self.paint_cell((r, c))
        self.place_dots()


class Panel(ttk.Frame):
    """One algorithm's view: a coloured header with live counters above a canvas."""

    def __init__(self, master: tk.Misc, model: Grid, name: str, color: str, cell: int):
        super().__init__(master)
        self.name = name
        self.color = color
        self.explored_color = blend(color, "#ffffff", 0.68)
        self.frontier_color = blend(color, "#ffffff", 0.22)

        head = tk.Frame(self, bg=COLOR_BG)
        head.pack(fill="x")
        tk.Label(head, text=name, fg="white", bg=color, font=FONT_BOLD,
                 padx=8, pady=1).pack(side="left")
        self.stats = tk.Label(head, text="ready", bg=COLOR_BG, fg=COLOR_TEXT,
                              font=FONT_SMALL, anchor="e")
        self.stats.pack(side="right", fill="x", expand=True)

        self.canvas = GridCanvas(self, model, cell)
        self.canvas.pack(pady=(2, 0))

    def apply(self, event: tuple) -> None:
        kind, payload = event
        if kind == "discover":
            self.canvas.paint_cell(payload, self.frontier_color)
        elif kind == "visit":
            self.canvas.paint_cell(payload, self.explored_color)
        elif kind == "done" and payload:
            for node in payload:
                self.canvas.paint_cell(node, COLOR_PATH)

    def render(self, runner: Runner) -> None:
        """Paint a runner's whole state at once (after an instant finish)."""
        for node in runner.frontier:
            self.canvas.paint_cell(node, self.frontier_color)
        for node in runner.explored:
            self.canvas.paint_cell(node, self.explored_color)
        if runner.path:
            for node in runner.path:
                self.canvas.paint_cell(node, COLOR_PATH)

    def show_stats(self, runner: Runner, race: Race) -> None:
        n = len(runner.explored)
        seconds = f"{runner.elapsed():.2f} s"
        if not runner.done:
            text = f"explored {n}  ·  frontier {len(runner.frontier)}  ·  {seconds}"
        elif runner.found:
            extra = runner.path_length - (race.optimal_length or 0)
            verdict = "shortest" if extra == 0 else f"{extra} longer than shortest"
            text = f"path {runner.path_length}  ·  explored {n}  ·  {verdict}  ·  {seconds}"
        else:
            why = "stuck at a local minimum" if (
                runner.name == "Hill Climbing" and race.optimal_length is not None) else "no path"
            text = f"{why}  ·  explored {n}  ·  {seconds}"
        self.stats.config(text=text)

    def reset(self) -> None:
        self.canvas.redraw()
        self.stats.config(text="ready")


class App:
    """The window: sidebar controls, one panel per racing algorithm, scoreboard."""

    COLUMNS = (
        ("algorithm", "Algorithm", 110, "w"),
        ("result", "Result", 150, "w"),
        ("explored", "Explored", 70, "e"),
        ("path", "Path length", 80, "e"),
        ("optimal", "Shortest?", 90, "center"),
        ("started", "Started", 100, "center"),
        ("finished", "Finished", 100, "center"),
        ("race_time", "Race time", 80, "e"),
        ("cpu", "Algorithm time", 100, "e"),
    )

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Maze Race")
        root.configure(bg=COLOR_BG)
        style = ttk.Style(root)
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=FONT)
        style.configure("TCheckbutton", background=COLOR_BG, font=FONT)
        style.configure("TButton", font=FONT)
        style.configure("Treeview", font=FONT, rowheight=20)
        style.configure("Treeview.Heading", font=FONT)

        self.grid = BY_NAME[DEFAULT_TEMPLATE].build()
        self.race: Race | None = None
        self.running = False
        self.after_id: str | None = None
        self.panels: list[Panel] = []
        self.panel_by_name: dict[str, Panel] = {}
        self.drag: str | None = None

        self.template_var = tk.StringVar(value=DEFAULT_TEMPLATE)
        self.note_var = tk.StringVar(value=BY_NAME[DEFAULT_TEMPLATE].note)
        self.help_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready. Pick a maze and press Start.")
        self.selected = {name: tk.BooleanVar(value=True) for name in ALGORITHMS}
        self.speed = tk.IntVar(value=12)
        self.braid = tk.IntVar(value=15)

        outer = ttk.Frame(root, padding=8)
        outer.pack(fill="both", expand=True)
        self.sidebar = ttk.Frame(outer, width=SIDEBAR_WIDTH)
        self.sidebar.pack(side="left", fill="y", padx=(0, 8))
        self.sidebar.pack_propagate(False)
        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True)
        self.panel_area = ttk.Frame(right)
        self.panel_area.pack(fill="both", expand=True)

        self._build_sidebar()
        self._build_scoreboard(right)
        self._build_legend(right)
        self.rebuild_panels()

        root.bind("<space>", lambda _e: self.toggle_run())
        root.bind("<Right>", lambda _e: self.step_once())
        root.bind("<Key-f>", lambda _e: self.finish_now())
        root.bind("<Escape>", lambda _e: self.reset())
        try:
            root.state("zoomed")
        except tk.TclError:
            pass

    # -- building the window ---------------------------------------------------------

    def _section(self, title: str) -> ttk.Frame:
        tk.Label(self.sidebar, text=title, font=FONT_BOLD, bg=COLOR_BG,
                 fg=COLOR_TEXT, anchor="w").pack(fill="x", pady=(10, 2))
        box = ttk.Frame(self.sidebar)
        box.pack(fill="x")
        return box

    def _build_sidebar(self) -> None:
        maze = self._section("Maze")
        picker = ttk.Combobox(maze, textvariable=self.template_var, state="readonly",
                              values=[t.name for t in TEMPLATES])
        picker.pack(fill="x")
        picker.bind("<<ComboboxSelected>>", self.load_template)
        tk.Label(maze, textvariable=self.note_var, wraplength=SIDEBAR_WIDTH - 10,
                 justify="left", anchor="nw", bg=COLOR_BG, fg=COLOR_MUTED,
                 font=FONT_SMALL, height=4).pack(fill="x", pady=(4, 0))
        rnd = ttk.Frame(maze)
        rnd.pack(fill="x")
        tk.Label(rnd, text="Random maze, braid %", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=FONT).pack(side="left")
        ttk.Button(rnd, text="Generate", command=self.generate_random).pack(side="right")
        tk.Scale(maze, from_=0, to=60, orient="horizontal", variable=self.braid,
                 bg=COLOR_BG, highlightthickness=0, troughcolor="#d6d3ca",
                 font=FONT_SMALL).pack(fill="x")

        algos = self._section("Algorithms in the race")
        for name in ALGORITHMS:
            row = ttk.Frame(algos)
            row.pack(fill="x", pady=1)
            tk.Label(row, bg=ALGO_COLORS[name], width=2).pack(side="left", padx=(2, 6))
            check = ttk.Checkbutton(row, text=name, variable=self.selected[name],
                                    command=self.on_selection_change)
            check.pack(side="left")
            check.bind("<Enter>", lambda _e, n=name: self.help_var.set(DESCRIPTIONS[n]))
            check.bind("<Leave>", lambda _e: self.help_var.set(""))
        tk.Label(algos, textvariable=self.help_var, wraplength=SIDEBAR_WIDTH - 10,
                 justify="left", anchor="nw", bg=COLOR_BG, fg=COLOR_MUTED,
                 font=FONT_SMALL, height=3).pack(fill="x", pady=(2, 0))

        race = self._section("Race")
        tk.Label(race, text="Speed (events per tick)", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=FONT, anchor="w").pack(fill="x")
        tk.Scale(race, from_=1, to=60, orient="horizontal", variable=self.speed,
                 bg=COLOR_BG, highlightthickness=0, troughcolor="#d6d3ca",
                 font=FONT_SMALL).pack(fill="x")
        buttons = ttk.Frame(race)
        buttons.pack(fill="x", pady=(4, 0))
        buttons.columnconfigure((0, 1), weight=1)
        self.run_button = ttk.Button(buttons, text="Start", command=self.toggle_run)
        self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 2), pady=2)
        ttk.Button(buttons, text="Step", command=self.step_once).grid(
            row=0, column=1, sticky="ew", padx=(2, 0), pady=2)
        ttk.Button(buttons, text="Finish now", command=self.finish_now).grid(
            row=1, column=0, sticky="ew", padx=(0, 2), pady=2)
        ttk.Button(buttons, text="Reset", command=self.reset).grid(
            row=1, column=1, sticky="ew", padx=(2, 0), pady=2)

        edit = self._section("Editing")
        tk.Label(edit, text=HINT, wraplength=SIDEBAR_WIDTH - 10, justify="left",
                 anchor="nw", bg=COLOR_BG, fg=COLOR_MUTED, font=FONT_SMALL).pack(fill="x")

        tk.Label(self.sidebar, textvariable=self.status_var, wraplength=SIDEBAR_WIDTH - 10,
                 justify="left", anchor="sw", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=FONT).pack(side="bottom", fill="x", pady=(8, 0))

    def _build_scoreboard(self, parent: ttk.Frame) -> None:
        tk.Label(parent, text="Scoreboard", font=FONT_BOLD, bg=COLOR_BG, fg=COLOR_TEXT,
                 anchor="w").pack(fill="x", pady=(6, 2))
        ids = [c[0] for c in self.COLUMNS]
        self.board = ttk.Treeview(parent, columns=ids, show="headings",
                                  height=len(ALGORITHMS), selectmode="none")
        for cid, heading, width, anchor in self.COLUMNS:
            self.board.heading(cid, text=heading)
            self.board.column(cid, width=width, anchor=anchor, stretch=(cid == "result"))
        for name, color in ALGO_COLORS.items():
            self.board.tag_configure(name, foreground=color)
        self.board.pack(fill="x")

    def _build_legend(self, parent: ttk.Frame) -> None:
        legend = ttk.Frame(parent)
        legend.pack(fill="x", pady=(6, 0))
        sample = ALGO_COLORS["BFS"]
        items = (
            ("Start", COLOR_START), ("Goal", COLOR_GOAL), ("Wall", COLOR_WALL),
            ("Frontier (algorithm colour)", blend(sample, "#ffffff", 0.22)),
            ("Explored (lighter tint)", blend(sample, "#ffffff", 0.68)),
            ("Final path", COLOR_PATH),
        )
        for text, color in items:
            tk.Label(legend, bg=color, width=2).pack(side="left", padx=(0, 4))
            tk.Label(legend, text=text, bg=COLOR_BG, fg=COLOR_TEXT,
                     font=FONT_SMALL).pack(side="left", padx=(0, 14))

    # -- panels -----------------------------------------------------------------------

    def _layout(self, count: int) -> tuple[int, int]:
        """Columns of panels and the cell size that fits them on this screen."""
        columns = 1 if count <= 1 else 2 if count <= 4 else 3
        rows = max(1, math.ceil(count / columns))
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        avail_w = screen_w - SIDEBAR_WIDTH - 70 - (columns - 1) * 8
        avail_h = screen_h - 120 - 215 - rows * 34
        cell = min(18, avail_w // (columns * self.grid.cols), avail_h // (rows * self.grid.rows))
        return columns, max(4, cell)

    def rebuild_panels(self) -> None:
        for widget in self.panel_area.winfo_children():
            widget.destroy()
        self.panels = []
        self.panel_by_name = {}
        names = [name for name in ALGORITHMS if self.selected[name].get()]
        if not names:
            tk.Label(self.panel_area, text="Tick at least one algorithm to race.",
                     bg=COLOR_BG, fg=COLOR_MUTED, font=FONT_BOLD).pack(pady=40)
        columns, cell = self._layout(len(names))
        for i, name in enumerate(names):
            panel = Panel(self.panel_area, self.grid, name, ALGO_COLORS[name], cell)
            panel.grid(row=i // columns, column=i % columns, padx=4, pady=4, sticky="n")
            self._bind_editing(panel.canvas)
            self.panels.append(panel)
            self.panel_by_name[name] = panel
        self._reset_scoreboard(names)

    def _reset_scoreboard(self, names: list[str]) -> None:
        self.board.delete(*self.board.get_children())
        for name in names:
            self.board.insert("", "end", iid=name, tags=(name,),
                              values=(name, "ready", "", "", "", "", "", "", ""))

    def _new_grid(self) -> None:
        self.pause()
        self.race = None
        self.rebuild_panels()
        self.set_status("New maze loaded. Press Start, or edit the maze first.")

    # -- maze choice --------------------------------------------------------------------

    def load_template(self, _event=None) -> None:
        template = BY_NAME.get(self.template_var.get())
        if template is None:
            return
        self.grid = template.build()
        self.note_var.set(template.note)
        self._new_grid()

    def generate_random(self) -> None:
        seed = random.randrange(1, 1_000_000)
        fraction = self.braid.get() / 100
        self.grid = generate(seed=seed, braid_fraction=fraction)
        self.template_var.set("")
        self.note_var.set(f"Random maze, seed {seed}, braid {self.braid.get()}%. "
                          "Perfect at 0%: every algorithm finds the same path.")
        self._new_grid()

    def on_selection_change(self) -> None:
        self.pause()
        self.race = None
        self.rebuild_panels()

    # -- editing the shared maze -------------------------------------------------------

    def _bind_editing(self, canvas: GridCanvas) -> None:
        canvas.bind("<Button-1>", lambda e, c=canvas: self.on_left_press(e, c))
        canvas.bind("<B1-Motion>", lambda e, c=canvas: self.on_left_drag(e, c))
        canvas.bind("<Button-3>", lambda e, c=canvas: self.on_right(e, c))
        canvas.bind("<B3-Motion>", lambda e, c=canvas: self.on_right(e, c))
        canvas.bind("<ButtonRelease-1>", self.on_release)
        canvas.bind("<ButtonRelease-3>", self.on_release)

    def _editable(self) -> bool:
        if self.race is not None:
            self.set_status("Press Reset before editing the maze.")
            return False
        return True

    def on_left_press(self, event: tk.Event, canvas: GridCanvas) -> None:
        node = canvas.node_at(event.x, event.y)
        if node is None or not self._editable():
            return
        if node == self.grid.start:
            self.drag = "start"
        elif node == self.grid.goal:
            self.drag = "goal"
        else:
            self.drag = "wall"
            self.paint(node, wall=True)

    def on_left_drag(self, event: tk.Event, canvas: GridCanvas) -> None:
        node = canvas.node_at(event.x, event.y)
        if node is None or self.race is not None:
            return
        if self.drag in ("start", "goal"):
            self.move_endpoint(self.drag, node)
        elif self.drag == "wall":
            self.paint(node, wall=True)

    def on_right(self, event: tk.Event, canvas: GridCanvas) -> None:
        node = canvas.node_at(event.x, event.y)
        if node is not None and self._editable():
            self.drag = "erase"
            self.paint(node, wall=False)

    def on_release(self, _event: tk.Event) -> None:
        self.drag = None

    def paint(self, node: Node, wall: bool) -> None:
        r, c = node
        changed = self.grid.set_wall(r, c) if wall else self.grid.clear_wall(r, c)
        if changed:
            for panel in self.panels:
                panel.canvas.paint_cell(node)

    def move_endpoint(self, which: str, node: Node) -> None:
        move = self.grid.move_start if which == "start" else self.grid.move_goal
        if move(*node):
            for panel in self.panels:
                panel.canvas.paint_cell(node)
                panel.canvas.place_dots()

    # -- running the race ----------------------------------------------------------------

    def _ensure_race(self) -> Race | None:
        if self.race is None:
            if not self.panels:
                self.set_status("Tick at least one algorithm first.")
                return None
            self.race = Race(self.grid, [(p.name, p.color) for p in self.panels])
        return self.race

    def toggle_run(self) -> None:
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self) -> None:
        race = self._ensure_race()
        if race is None or race.finished:
            return
        if race.started_at is None:
            race.start()          # the clocks start when Start is pressed
        self.running = True
        self.run_button.config(text="Pause")
        self.set_status("Racing. Space pauses.")
        self._schedule()

    def pause(self) -> None:
        self.running = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.race is not None and not self.race.finished:
            self.run_button.config(text="Resume" if self.race.started_at else "Start")
            if self.race.started_at:
                self.set_status("Paused. Right arrow steps one event at a time.")
        else:
            self.run_button.config(text="Start")

    def _schedule(self) -> None:
        self.after_id = self.root.after(TICK_MS, self.tick)

    def tick(self) -> None:
        self.after_id = None
        if not self.running or self.race is None:
            return
        self._advance(self.speed.get())
        if self.race.finished:
            self._finish()
        else:
            self._schedule()

    def _advance(self, k: int) -> None:
        assert self.race is not None
        for runner, event in self.race.step(k):
            self.panel_by_name[runner.name].apply(event)
        self.refresh_stats()

    def step_once(self) -> None:
        if self.running:
            self.pause()
        race = self._ensure_race()
        if race is not None and not race.finished:
            self._advance(1)
            self.run_button.config(text="Resume")

    def finish_now(self) -> None:
        race = self._ensure_race()
        if race is None:
            return
        self.pause()
        race.run_to_completion()
        for runner in race.runners:
            self.panel_by_name[runner.name].render(runner)
        self.refresh_stats()
        self._finish()

    def _finish(self) -> None:
        self.running = False
        self.run_button.config(text="Start")
        assert self.race is not None
        winners = [r for r in self.race.runners if r.found]
        if winners:
            first = min(winners, key=lambda r: r.finished_at)
            fewest = min(winners, key=lambda r: len(r.explored))
            self.set_status(f"Finished. First to the goal: {first.name}. "
                            f"Fewest cells explored: {fewest.name} ({len(fewest.explored)}). "
                            "Reset to race again or edit the maze.")
        else:
            self.set_status("Finished. Nobody found a path. Reset to try again.")

    def reset(self) -> None:
        self.pause()
        self.race = None
        self.run_button.config(text="Start")
        for panel in self.panels:
            panel.reset()
        self._reset_scoreboard([p.name for p in self.panels])
        self.set_status("Reset. The maze can be edited again.")

    # -- stats -----------------------------------------------------------------------------

    def refresh_stats(self) -> None:
        race = self.race
        if race is None:
            return
        for runner in race.runners:
            self.panel_by_name[runner.name].show_stats(runner, race)
            self.board.item(runner.name, values=self._row(runner, race))

    @staticmethod
    def _row(runner: Runner, race: Race) -> tuple:
        if not runner.done:
            result = "running"
        elif runner.found:
            result = "path found"
        elif runner.name == "Hill Climbing" and race.optimal_length is not None:
            result = "stuck at a local minimum"
        else:
            result = "no path exists"
        optimal = race.is_optimal(runner)
        if optimal is None:
            shortest = ""
        elif optimal:
            shortest = "yes"
        else:
            shortest = f"no (+{runner.path_length - race.optimal_length})"
        return (
            runner.name,
            result,
            len(runner.explored),
            "" if runner.path_length is None else runner.path_length,
            shortest,
            fmt_clock(runner.started_at),
            fmt_clock(runner.finished_at),
            f"{runner.elapsed():.3f} s" if runner.started_at else "",
            f"{runner.compute_seconds * 1000:.2f} ms" if runner.started_at else "",
        )

    def set_status(self, text: str) -> None:
        self.status_var.set(text)


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
