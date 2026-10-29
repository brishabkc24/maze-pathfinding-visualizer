"""Maze Race: the Tkinter grid editor.

Left-drag paints walls, right-drag erases them, and the start and goal dots
can be dragged to other cells. The pathfinding algorithms arrive in later
roadmap items; this module owns only the view and the mouse handling.

Run with ``python app.py``.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from grid import Grid, Node

COLS, ROWS = 41, 25
CELL = 18  # pixels per cell

COLOR_WALL = "#1f2933"
COLOR_OPEN = "#f5f5f0"
COLOR_GRIDLINE = "#dddbd3"
COLOR_START = "#2e9e4f"
COLOR_GOAL = "#d64545"
COLOR_BG = "#e9e7e0"

HINT = ("Left-drag paints walls   ·   right-drag erases   ·   "
        "drag the green (start) and red (goal) dots to move them")


class GridCanvas(tk.Canvas):
    """Draws one :class:`Grid`.

    Every cell rectangle is created once, here in ``__init__``. Afterwards
    cells are only recolored with ``itemconfig`` and the start and goal dots
    are moved with ``coords``; nothing is deleted and redrawn. That is what
    keeps a Tkinter canvas smooth once thousands of cells are being animated.
    """

    def __init__(self, master: tk.Misc, model: Grid, cell: int = CELL, **kwargs):
        super().__init__(master, width=model.cols * cell, height=model.rows * cell,
                         highlightthickness=0, bg=COLOR_OPEN, **kwargs)
        self.model = model
        self.cell = cell
        self.rects = [
            [self.create_rectangle(c * cell, r * cell, (c + 1) * cell, (r + 1) * cell,
                                   fill=COLOR_OPEN, outline=COLOR_GRIDLINE)
             for c in range(model.cols)]
            for r in range(model.rows)
        ]
        self._dot_pad = max(2, cell // 5)
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
        """Move the start and goal dots to where the model says they are."""
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


class App:
    """The editor window: a toolbar, one :class:`GridCanvas` and a hint line."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Maze Race")
        root.configure(bg=COLOR_BG)
        root.resizable(False, False)
        style = ttk.Style(root)
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG)

        self.model = Grid(COLS, ROWS)
        # What the held mouse button is doing: "wall", "erase", "start" or "goal".
        self.drag: str | None = None

        bar = ttk.Frame(root, padding=(10, 8, 10, 4))
        bar.pack(fill="x")
        ttk.Button(bar, text="Clear walls", command=self.clear_walls).pack(side="left")
        self.status = ttk.Label(bar, anchor="e")
        self.status.pack(side="right")

        self.canvas = GridCanvas(root, self.model)
        self.canvas.pack(padx=10, pady=4)
        self.canvas.bind("<Button-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<Button-3>", self.on_right)
        self.canvas.bind("<B3-Motion>", self.on_right)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonRelease-3>", self.on_release)

        ttk.Label(root, text=HINT).pack(pady=(2, 10))
        self.update_status()

    # -- mouse ------------------------------------------------------------------

    def on_left_press(self, event: tk.Event) -> None:
        node = self.canvas.node_at(event.x, event.y)
        if node is None:
            return
        if node == self.model.start:
            self.drag = "start"
        elif node == self.model.goal:
            self.drag = "goal"
        else:
            self.drag = "wall"
            self.paint(node, wall=True)

    def on_left_drag(self, event: tk.Event) -> None:
        node = self.canvas.node_at(event.x, event.y)
        if node is None:
            return
        if self.drag in ("start", "goal"):
            self.move_endpoint(self.drag, node)
        elif self.drag == "wall":
            self.paint(node, wall=True)

    def on_right(self, event: tk.Event) -> None:
        node = self.canvas.node_at(event.x, event.y)
        if node is not None:
            self.drag = "erase"
            self.paint(node, wall=False)

    def on_release(self, _event: tk.Event) -> None:
        self.drag = None

    # -- edits ------------------------------------------------------------------

    def paint(self, node: Node, wall: bool) -> None:
        r, c = node
        changed = self.model.set_wall(r, c) if wall else self.model.clear_wall(r, c)
        if changed:
            self.canvas.paint_cell(node)
            self.update_status()

    def move_endpoint(self, which: str, node: Node) -> None:
        move = self.model.move_start if which == "start" else self.model.move_goal
        if move(*node):
            self.canvas.paint_cell(node)   # a wall under the dot was cleared
            self.canvas.place_dots()
            self.update_status()

    def clear_walls(self) -> None:
        self.model.clear_walls()
        self.canvas.redraw()
        self.update_status()

    def update_status(self) -> None:
        m = self.model
        self.status.config(
            text=f"Walls: {m.wall_count}    Start: {m.start}    Goal: {m.goal}")


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
