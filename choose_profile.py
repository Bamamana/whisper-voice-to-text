#!/usr/bin/env python3
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk


class ProfileChooser:
    def __init__(self, current_profile: str) -> None:
        self.current_profile = current_profile if current_profile in {"auto", "cpu", "amd", "nvidia"} else "auto"
        self.selection: str | None = None

        self.root = tk.Tk()
        self.root.title("Whisper Launch Profile")
        self.root.geometry("380x280")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)

        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Choose Whisper hardware profile").pack(anchor="w")
        ttk.Label(frame, text=f"Current installed profile: {self.current_profile}").pack(anchor="w", pady=(6, 12))

        self.profile_var = tk.StringVar(value=self.current_profile)

        choices = [
            (f"Current ({self.current_profile})", self.current_profile),
            ("CPU", "cpu"),
            ("AMD", "amd"),
            ("NVIDIA", "nvidia"),
        ]
        seen: set[str] = set()
        for label, value in choices:
            if value in seen:
                continue
            seen.add(value)
            ttk.Radiobutton(frame, text=label, value=value, variable=self.profile_var).pack(anchor="w", pady=2)

        ttk.Label(
            frame,
            text="Changing profile rebuilds the local Whisper environment before launch.",
            wraplength=320,
        ).pack(anchor="w", pady=(12, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(16, 0))
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(side=tk.RIGHT)
        next_button = ttk.Button(buttons, text="Next", command=self.launch)
        next_button.pack(side=tk.RIGHT, padx=(0, 8))

        self.root.bind("<Return>", lambda _event: self.launch())
        self.root.bind("<Escape>", lambda _event: self.cancel())
        next_button.focus_set()

    def launch(self) -> None:
        self.selection = self.profile_var.get()
        self.root.destroy()

    def cancel(self) -> None:
        self.selection = None
        self.root.destroy()

    def run(self) -> str | None:
        self.root.mainloop()
        return self.selection


def main() -> int:
        current_profile = sys.argv[1] if len(sys.argv) > 1 else "auto"
        chooser = ProfileChooser(current_profile)
        selection = chooser.run()
        if selection:
            print(selection)
            return 0
        return 1


if __name__ == "__main__":
    raise SystemExit(main())