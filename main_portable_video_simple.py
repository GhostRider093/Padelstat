"""Entry point for the lightweight video-centric portable build."""

from __future__ import annotations

import sys
import tkinter as tk


def main() -> None:
    from app.ui.main_window import MainWindow

    root = tk.Tk()
    MainWindow(root, ui_mode="portable_video_simple", window_title="PFPADEL Video Simple")
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
