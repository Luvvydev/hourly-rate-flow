import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import json
from pathlib import Path


class LedgerFlow:
    def __init__(self, root):
        self.root = root
        self.root.title("LedgerFlow - Hourly Earnings Tracker")
        self.root.geometry("1000x750")

        # Database setup
        self.db_path = Path.home() / ".ledgerflow.db"
        self.init_db()

        # Load settings
        self.settings = self.load_settings()

        # Current period
        self.current_period_start = self.settings.get(
            "current_period_start",
            datetime.now().strftime("%Y-%m-%d"),
        )

        # User-configurable rates with defaults
        # - store avg_tips always (even if tips disabled) so re-enabling tips preserves it
        self.use_tips = bool(self.settings.get("use_tips", True))
        self.base_rate = float(self.settings.get("base_rate", 7.00))
        self.avg_tips = float(self.settings.get("avg_tips", 23.15))

        # Derived (never persisted)
        self.effective_rate = 0.0
        self.recalc_effective_rate()

        # UI Setup
        self.setup_ui()
        self.load_period_data()

        # Auto-focus hours field on launch
        self.root.after(100, lambda: self.hours_entry.focus_set())

    # -------------------- Settings & Persistence --------------------

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    hours REAL NOT NULL,
                    note TEXT,
                    period_start TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS periods (
                    period_start TEXT PRIMARY KEY,
                    archived INTEGER DEFAULT 0
                )
            """
            )

    def load_settings(self):
        settings_path = Path.home() / ".ledgerflow_settings.json"
        if not settings_path.exists():
            return {}

        try:
            with open(settings_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Corrupt JSON: preserve it for debugging, then reset to defaults
            try:
                backup = settings_path.with_suffix(".json.corrupt")
                settings_path.rename(backup)
                messagebox.showwarning(
                    "Settings Reset",
                    f"Your settings file was corrupted and has been renamed to:\n{backup}\n\n"
                    "Defaults will be used.",
                )
            except Exception:
                # If rename fails, still fall back to defaults
                messagebox.showwarning(
                    "Settings Reset",
                    "Your settings file appears corrupted. Defaults will be used.",
                )
            return {}
        except OSError as e:
            messagebox.showwarning(
                "Settings Unavailable",
                f"Could not read settings file:\n{e}\n\nDefaults will be used.",
            )
            return {}

    def save_settings(self):
        settings_path = Path.home() / ".ledgerflow_settings.json"
        self.settings["current_period_start"] = self.current_period_start
        self.settings["use_tips"] = self.use_tips
        self.settings["base_rate"] = self.base_rate
        self.settings["avg_tips"] = self.avg_tips  # store even if tips are off
        # IMPORTANT: do NOT store effective_rate (derived)

        with open(settings_path, "w") as f:
            json.dump(self.settings, f, indent=2)

    def recalc_effective_rate(self):
        """Recalculate derived effective rate from base_rate/use_tips/avg_tips."""
        tips_component = self.avg_tips if self.use_tips else 0.0
        self.effective_rate = float(self.base_rate) + float(tips_component)

    def update_rates(self):
        """Apply current in-memory settings to derived rate + UI."""
        self.recalc_effective_rate()
        self.save_settings()
        self.update_rate_display()
        self.load_period_data()

    # -------------------- Settings Window --------------------

    def show_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("400x450")
        settings_win.transient(self.root)
        settings_win.grab_set()

        # Center the window
        settings_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (settings_win.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (settings_win.winfo_height() // 2)
        settings_win.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(settings_win, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Rate Configuration", font=("Helvetica", 14, "bold")).pack(pady=(0, 20))

        # Base Rate
        rate_frame = ttk.LabelFrame(main_frame, text="Base Hourly Rate", padding=10)
        rate_frame.pack(fill=tk.X, pady=(0, 15))

        self.base_rate_var = tk.DoubleVar(value=self.base_rate)
        base_rate_spin = ttk.Spinbox(
            rate_frame,
            from_=0.0,
            to=1000.0,
            increment=0.25,
            textvariable=self.base_rate_var,
            width=10,
            format="%.2f",
        )
        base_rate_spin.pack(pady=5)
        ttk.Label(rate_frame, text="Your hourly wage before tips", foreground="gray").pack()

        # Tips Configuration
        tips_frame = ttk.LabelFrame(main_frame, text="Tips Configuration", padding=10)
        tips_frame.pack(fill=tk.X, pady=(0, 15))

        self.use_tips_var = tk.BooleanVar(value=self.use_tips)
        tips_check = ttk.Checkbutton(
            tips_frame,
            text="Include tips in calculations",
            variable=self.use_tips_var,
            command=lambda: self.toggle_tips_settings(settings_win),
        )
        tips_check.pack(anchor=tk.W, pady=(0, 10))

        # Average tips (shown/hidden based on checkbox, value preserved always)
        self.avg_tips_var = tk.DoubleVar(value=self.avg_tips)

        self.tips_spin_frame = ttk.Frame(tips_frame)
        self.tips_spin_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(self.tips_spin_frame, text="Average tips per hour:").pack(side=tk.LEFT, padx=(0, 10))
        self.avg_tips_spin = ttk.Spinbox(
            self.tips_spin_frame,
            from_=0.0,
            to=500.0,
            increment=0.25,
            textvariable=self.avg_tips_var,
            width=10,
            format="%.2f",
        )
        self.avg_tips_spin.pack(side=tk.LEFT)

        if not self.use_tips:
            self.tips_spin_frame.pack_forget()

        # Effective rate display (created ONCE, updated via .config)
        display_frame = ttk.Frame(main_frame)
        display_frame.pack(fill=tk.X, pady=(10, 0))

        self.effective_rate_label = ttk.Label(
            display_frame,
            text="",
            font=("Helvetica", 12, "bold"),
            foreground="#2E7D32",
        )
        self.effective_rate_label.pack()

        self.effective_rate_sub_label = ttk.Label(
            display_frame,
            text="",
            font=("Helvetica", 10),
            foreground="gray",
        )
        self.effective_rate_sub_label.pack()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(
            btn_frame,
            text="Save & Apply",
            command=lambda: self.save_new_settings(settings_win),
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(btn_frame, text="Cancel", command=settings_win.destroy).pack(side=tk.RIGHT)

        # Configure styles (do once; safe to call repeatedly but we keep it centralized)
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))

        # Bind changes to update effective rate display (trace_add is modern)
        self.base_rate_var.trace_add("write", lambda *_: self.update_effective_rate_display())
        self.avg_tips_var.trace_add("write", lambda *_: self.update_effective_rate_display())
        self.use_tips_var.trace_add("write", lambda *_: self.update_effective_rate_display())

        # Initialize display
        self.update_effective_rate_display()

    def toggle_tips_settings(self, settings_win):
        """Show/hide tips input based on checkbox (no toplevel hunting)."""
        if self.use_tips_var.get():
            self.tips_spin_frame.pack(fill=tk.X, pady=(5, 0))
        else:
            self.tips_spin_frame.pack_forget()
        self.update_effective_rate_display()

    def update_effective_rate_display(self):
        """Update the effective rate display in settings window (no widget recreation)."""
        try:
            base = float(self.base_rate_var.get())
        except Exception:
            return

        try:
            tips_val = float(self.avg_tips_var.get())
        except Exception:
            tips_val = 0.0

        use_tips = bool(self.use_tips_var.get())
        tips_component = tips_val if use_tips else 0.0
        effective = base + tips_component

        self.effective_rate_label.config(text=f"Effective Rate: ${effective:.2f}/hour")

        if use_tips:
            self.effective_rate_sub_label.config(text=f"${base:.2f} base + ${tips_val:.2f} tips")
        else:
            self.effective_rate_sub_label.config(text=f"${base:.2f} base (tips excluded)")

    def save_new_settings(self, settings_win):
        """Save new settings from settings window."""
        try:
            base = float(self.base_rate_var.get())
            tips = float(self.avg_tips_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for rates.")
            return

        use_tips = bool(self.use_tips_var.get())

        if base < 0 or tips < 0:
            messagebox.showerror("Error", "Rates cannot be negative.")
            return

        self.base_rate = base
        self.avg_tips = tips  # preserve even if tips disabled
        self.use_tips = use_tips

        self.update_rates()
        settings_win.destroy()
        messagebox.showinfo("Success", "Settings updated successfully!")

    def update_rate_display(self):
        """Update the rate display in the main window."""
        if self.use_tips:
            rate_text = f"Rate: ${self.effective_rate:.2f}/hr (${self.base_rate:.2f} + ${self.avg_tips:.2f} avg tips)"
        else:
            rate_text = f"Rate: ${self.effective_rate:.2f}/hr (tips excluded)"
        self.rate_label.config(text=rate_text)

    # -------------------- UI --------------------

    def setup_ui(self):
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Helvetica", 14, "bold"))
        style.configure("Metric.TLabel", font=("Helvetica", 12))
        style.configure("Rate.TLabel", font=("Helvetica", 10))

        # Root expansion
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        # Layout rows:
        # 0 header
        # 1 input
        # 2 metrics
        # 3 visualization
        # 4 entries
        main.rowconfigure(3, weight=0)  # visualization fixed-ish height
        main.rowconfigure(4, weight=1)  # entries expand

        # --- Header with Settings Button ---
        header_frame = ttk.Frame(main)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        header_frame.columnconfigure(0, weight=1)

        ttk.Label(header_frame, text="Hourly Earnings Tracker", font=("Helvetica", 16, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        ttk.Button(header_frame, text="⚙ Settings", command=self.show_settings, width=10).grid(
            row=0, column=1, sticky="e"
        )

        # --- Input ---
        input_frame = ttk.LabelFrame(main, text="Log Hours", padding=10)
        input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(input_frame, text="Date:").grid(row=0, column=0, sticky="w")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(input_frame, textvariable=self.date_var, width=12).grid(row=0, column=1, padx=(5, 20))

        ttk.Label(input_frame, text="Hours:").grid(row=0, column=2, sticky="w")
        self.hours_var = tk.StringVar()
        self.hours_entry = ttk.Entry(input_frame, textvariable=self.hours_var, width=10)
        self.hours_entry.grid(row=0, column=3, padx=(5, 20))

        # Quick buttons
        quick = ttk.Frame(input_frame)
        quick.grid(row=1, column=2, columnspan=5, sticky="w", pady=(5, 0))
        for h in range(1, 9):
            ttk.Button(quick, text=f"{h}h", width=4, command=lambda v=h: self.hours_var.set(str(v))).pack(
                side=tk.LEFT, padx=2
            )

        # Notes (progressive)
        self.note_var = tk.StringVar()
        self.note_visible = False

        self.note_button = ttk.Button(input_frame, text="➕ Add Note", command=self.toggle_note, width=10)
        self.note_button.grid(row=0, column=4, padx=(5, 10))

        self.note_entry = ttk.Entry(input_frame, textvariable=self.note_var, width=25)

        ttk.Button(input_frame, text="Add Entry", command=self.add_entry).grid(row=0, column=7, padx=(10, 0))

        self.hours_entry.bind("<Return>", lambda e: self.add_entry())
        self.note_entry.bind("<Return>", lambda e: self.add_entry())

        # --- Metrics ---
        metrics = ttk.Frame(main)
        metrics.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        metrics.columnconfigure(0, weight=1)
        metrics.columnconfigure(1, weight=1)

        left = ttk.Frame(metrics)
        left.grid(row=0, column=0, sticky="w", padx=(0, 50))

        ttk.Label(left, text="CURRENT PERIOD", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.hours_label = ttk.Label(left, text="Hours: 0.0", style="Metric.TLabel")
        self.hours_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        self.earnings_label = ttk.Label(left, text="Projected: $0.00", style="Metric.TLabel")
        self.earnings_label.grid(row=2, column=0, sticky="w", pady=(5, 0))

        self.momentum_label = ttk.Label(left, text="", font=("Helvetica", 11, "bold"), foreground="#2E7D32")
        self.momentum_label.grid(row=3, column=0, sticky="w", pady=(5, 0))

        # Rate display
        self.rate_label = ttk.Label(left, text="", style="Rate.TLabel")
        self.rate_label.grid(row=4, column=0, sticky="w", pady=(5, 0))
        self.update_rate_display()

        ttk.Label(
            left,
            text="Projection based on configured rates" + (" and average tips" if self.use_tips else ""),
            style="Rate.TLabel",
            foreground="gray",
        ).grid(row=5, column=0, sticky="w", pady=(2, 0))

        right = ttk.Frame(metrics)
        right.grid(row=0, column=1, sticky="w")

        ttk.Label(right, text="PERIOD CONTROLS", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        self.period_info_label = ttk.Label(right, text=f"Started: {self.current_period_start}", style="Rate.TLabel")
        self.period_info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        ttk.Button(right, text="Start New Period", command=self.start_new_period).grid(row=2, column=0, sticky="w", pady=(5, 0))
        ttk.Button(right, text="Export Data", command=self.export_data).grid(row=3, column=0, sticky="w", pady=(5, 0))
        ttk.Button(right, text="Clear All Data", command=self.clear_all_data).grid(row=4, column=0, sticky="w", pady=(5, 0))

        # --- Visualization ---
        vis = ttk.LabelFrame(main, text="Progress Visualization", padding=10)
        vis.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        vis.columnconfigure(0, weight=1)
        vis.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(vis, height=200, bg="white")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # --- Entries ---
        entries = ttk.LabelFrame(main, text="Recent Entries", padding=10)
        entries.grid(row=4, column=0, columnspan=2, sticky="nsew")
        entries.columnconfigure(0, weight=1)
        entries.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(entries, columns=("date", "hours", "note"), show="headings", height=8)
        self.tree.heading("date", text="Date")
        self.tree.heading("hours", text="Hours")
        self.tree.heading("note", text="Note")

        self.tree.column("date", width=110, anchor="w")
        self.tree.column("hours", width=80, anchor="center")
        self.tree.column("note", width=400, anchor="w")

        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(entries, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    # -------------------- Behavior --------------------

    def toggle_note(self):
        if self.note_visible:
            self.note_entry.grid_remove()
            self.note_button.config(text="➕ Add Note")
            self.note_visible = False
        else:
            self.note_entry.grid(row=0, column=5, columnspan=2, padx=(0, 10), sticky="w")
            self.note_button.config(text="✕ Hide Note")
            self.note_visible = True
            self.note_entry.focus_set()

    def validate_hours(self, value):
        try:
            v = float(value)
            return v if v > 0 else None
        except ValueError:
            return None

    def add_entry(self):
        hours = self.validate_hours(self.hours_var.get().strip())
        if hours is None:
            messagebox.showerror("Error", "Hours must be a positive number.")
            return

        earned_today = hours * self.effective_rate

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO entries (date, hours, note, period_start) VALUES (?, ?, ?, ?)",
                (self.date_var.get(), hours, self.note_var.get(), self.current_period_start),
            )

        self.hours_var.set("")
        self.note_var.set("")
        if self.note_visible:
            self.toggle_note()

        self.load_period_data()
        self.flash_momentum(earned_today)
        self.hours_entry.focus_set()

    def flash_momentum(self, amount):
        self.momentum_label.config(text=f"+ ${amount:.2f} today")
        self.root.after(2000, lambda: self.momentum_label.config(text=""))

    # -------------------- Data Loading --------------------

    def load_period_data(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT SUM(hours) FROM entries WHERE period_start = ?", (self.current_period_start,))
            total_hours = c.fetchone()[0] or 0.0

            c.execute(
                "SELECT date, hours, note FROM entries WHERE period_start = ? ORDER BY date DESC, created_at DESC",
                (self.current_period_start,),
            )
            entries = c.fetchall()

        projected = total_hours * self.effective_rate
        self.hours_label.config(text=f"Hours: {total_hours:.1f}")
        self.earnings_label.config(text=f"Projected: ${projected:.2f}")

        self.tree.delete(*self.tree.get_children())
        for row in entries:
            self.tree.insert("", "end", values=row)

        self.update_visualization(total_hours, entries)
        self.save_settings()

    def update_visualization(self, total_hours, entries):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        projected = total_hours * self.effective_rate

        font_size = int(min(54, max(36, 36 + int(projected / 1000))))

        if entries:
            last = entries[:10]
            max_hours = max(r[1] for r in last)
            max_bar_h = h - 40
            denom = max(100.0, float(max_hours) * 10.0)
            x = 50
            bar_w = 20

            for _, hours, _ in last:
                bar_h = float(hours) * max_bar_h / denom
                self.canvas.create_rectangle(
                    x,
                    h - 20 - bar_h,
                    x + bar_w,
                    h - 20,
                    fill="#CFE3F1",
                    outline="",
                )
                self.canvas.create_text(
                    x + bar_w / 2,
                    h - 10,
                    text=f"{hours}h",
                    fill="#666666",
                    font=("Helvetica", 8),
                )
                x += (bar_w + 10)

        self.canvas.create_text(
            w - 120,
            h // 2,
            text=f"${projected:.2f}",
            font=("Helvetica", font_size, "bold"),
            fill="#2E7D32",
        )

        self.canvas.create_text(
            w - 120,
            (h // 2) + 35,
            text="Projected Earnings",
            font=("Helvetica", 10),
            fill="gray",
        )

    # -------------------- Periods --------------------

    def start_new_period(self):
        if not messagebox.askyesno("New Period", "Start a new period?"):
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO periods (period_start, archived) VALUES (?, 1)",
                (self.current_period_start,),
            )

        self.current_period_start = datetime.now().strftime("%Y-%m-%d")
        self.period_info_label.config(text=f"Started: {self.current_period_start}")
        self.load_period_data()

    def clear_all_data(self):
        if not messagebox.askyesno(
            "Clear All Data",
            "This will permanently delete ALL data.\n\nContinue?",
        ):
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM entries")
                conn.execute("DELETE FROM periods")

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("VACUUM")
            except Exception:
                pass

            self.current_period_start = datetime.now().strftime("%Y-%m-%d")
            self.date_var.set(self.current_period_start)
            self.period_info_label.config(text=f"Started: {self.current_period_start}")
            self.save_settings()

            self.momentum_label.config(text="")

            self.load_period_data()
            self.hours_entry.focus_set()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear data: {e}")

    # -------------------- Export --------------------

    def export_data(self):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT period_start, date, hours, note, created_at FROM entries ORDER BY period_start, date"
            ).fetchall()

        rate_info = f"Rate: ${self.effective_rate:.2f}/hr (Base: ${self.base_rate:.2f}"
        if self.use_tips:
            rate_info += f", Tips: ${self.avg_tips:.2f})"
        else:
            rate_info += ", Tips excluded)"

        export = [
            "LedgerFlow Data Export",
            f"Generated: {datetime.now()}",
            rate_info,
            "=" * 50,
            "Period,Date,Hours,Note,Logged_At",
        ]
        export += [",".join(map(str, r)) for r in rows]

        win = tk.Toplevel(self.root)
        win.title("Export Data")
        win.geometry("700x450")

        txt = tk.Text(win, wrap=tk.NONE)
        txt.insert("1.0", "\n".join(export))
        txt.config(state=tk.DISABLED)

        scroll_y = ttk.Scrollbar(win, orient=tk.VERTICAL, command=txt.yview)
        scroll_x = ttk.Scrollbar(win, orient=tk.HORIZONTAL, command=txt.xview)
        txt.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        txt.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)


def main():
    root = tk.Tk()
    app = LedgerFlow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
