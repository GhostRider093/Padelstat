"""Entry point for the lightweight portable manual-entry build."""

from __future__ import annotations

import sys
import tkinter as tk

from app.ui.simple_portable_window import PortableSimpleWindow


def main() -> None:
    root = tk.Tk()
    PortableSimpleWindow(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
