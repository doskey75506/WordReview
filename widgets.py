"""Reusable Tk widgets shared by the practice and review screens."""

from __future__ import annotations

import calendar
from datetime import date, datetime

import tkinter as tk
from tkinter import ttk


class CalendarPopup(tk.Toplevel):
    """Month calendar that writes an ISO date into a StringVar (empty string clears)."""

    def __init__(self, master: tk.Misc, variable: tk.StringVar, on_change=None) -> None:
        super().__init__(master)
        self.title("Select date")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.variable = variable
        self.on_change = on_change
        try:
            current = datetime.strptime(variable.get(), "%Y-%m-%d").date()
        except ValueError:
            current = date.today()
        self.current = current.replace(day=1)
        self._build_header()
        self._build_grid()
        self._build_footer()
        self.geometry(f"+{master.winfo_rootx()}+{master.winfo_rooty()}")
        self._day_buttons: list[ttk.Button] = []
        self._render_days()

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill="x")
        ttk.Button(header, text="« Y", width=4, command=lambda: self._shift(years=-1)).pack(side="left")
        ttk.Button(header, text="« M", width=4, command=lambda: self._shift(months=-1)).pack(side="left", padx=2)
        self.month_label = ttk.Label(header, text="", width=16, anchor="center")
        self.month_label.pack(side="left", expand=True)
        ttk.Button(header, text="M »", width=4, command=lambda: self._shift(months=1)).pack(side="left", padx=2)
        ttk.Button(header, text="Y »", width=4, command=lambda: self._shift(years=1)).pack(side="left")

    def _build_grid(self) -> None:
        self.grid_frame = ttk.Frame(self, padding=8)
        self.grid_frame.pack()
        for column, name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            ttk.Label(self.grid_frame, text=name, width=4, anchor="center").grid(row=0, column=column, padx=1, pady=1)

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, padding=(8, 0, 8, 8))
        footer.pack(fill="x")
        ttk.Button(footer, text="Today", command=self._pick_today).pack(side="left")
        ttk.Button(footer, text="Clear", command=self._clear).pack(side="left", padx=(6, 0))
        ttk.Button(footer, text="Close", command=self.destroy).pack(side="right")

    def _shift(self, months: int = 0, years: int = 0) -> None:
        month = self.current.month + months
        year = self.current.year + years + (month - 1) // 12
        self.current = date(year, (month - 1) % 12 + 1, 1)
        self._render_days()

    def _render_days(self) -> None:
        self.month_label.configure(text=self.current.strftime("%B %Y"))
        for button in self._day_buttons:
            button.destroy()
        self._day_buttons = []
        offset = self.current.weekday()
        days = calendar.monthrange(self.current.year, self.current.month)[1]
        for day in range(1, days + 1):
            slot = offset + day - 1
            button = ttk.Button(
                self.grid_frame,
                text=str(day),
                width=4,
                command=lambda chosen=day: self._pick(chosen),
            )
            button.grid(row=slot // 7 + 1, column=slot % 7, padx=1, pady=1)
            self._day_buttons.append(button)

    def _pick(self, day: int) -> None:
        self.variable.set(date(self.current.year, self.current.month, day).isoformat())
        self._notify()
        self.destroy()

    def _pick_today(self) -> None:
        self.variable.set(date.today().isoformat())
        self._notify()
        self.destroy()

    def _clear(self) -> None:
        self.variable.set("")
        self._notify()
        self.destroy()

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()


class DateField(ttk.Frame):
    """Calendar-driven date input; the bound StringVar holds YYYY-MM-DD or ""."""

    def __init__(self, master: tk.Misc, variable: tk.StringVar, on_change=None) -> None:
        super().__init__(master)
        self.variable = variable
        self.on_change = on_change
        self.display = tk.StringVar()
        self._sync()
        self.button = ttk.Button(self, textvariable=self.display, command=self._open_popup)
        self.button.pack(side="left")
        ttk.Button(self, text="✕", width=2, command=self._clear).pack(side="left", padx=(4, 0))

    def _sync(self) -> None:
        self.display.set(self.variable.get() or "Not set")

    def _clear(self) -> None:
        self.variable.set("")
        self._sync()
        if self.on_change:
            self.on_change()

    def _open_popup(self) -> None:
        CalendarPopup(self, self.variable, on_change=self._changed)

    def _changed(self) -> None:
        self._sync()
        if self.on_change:
            self.on_change()
