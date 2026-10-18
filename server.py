import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import sys
import os

# ================== COLOR THEME (Black) ==================
BG        = "#0a0a0a"   # main black
CARD_BG   = "#151515"   # card black
FG        = "#e0e0e0"   # text
ACCENT    = "#00ff88"   # green LED / running
OFF       = "#1a3a1a"   # LED off (dark green)
BTN_BG    = "#222222"
BTN_HOVER = "#333333"


class BotPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ Telegram Bot Deploy Panel")
        self.root.geometry("760x680")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.bots = {}   # path -> {card, led, circle, status, proc, running}
        self._build_header()
        self._build_list()

    # ---------------- UI BUILD ----------------
    def _build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(20, 8))

        tk.Label(header, text="⚡ BOT DEPLOY PANEL", bg=BG, fg=ACCENT,
                 font=("Consolas", 18, "bold")).pack(anchor="w")
        tk.Label(header, text="Telegram bot deploy & manage koro",
                 bg=BG, fg="#666666", font=("Consolas", 10)).pack(anchor="w", pady=(2, 0))

        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=20, pady=15)

        self.file_entry = tk.Entry(row, bg=CARD_BG, fg=FG, insertbackground=FG,
                                   relief="flat", font=("Consolas", 10))
        self.file_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))

        tk.Button(row, text="📁 CHOOSE .py", command=self.choose_file,
                  bg=BTN_BG, fg=FG, activebackground=BTN_HOVER, activeforeground=ACCENT,
                  relief="flat", font=("Consolas", 10, "bold"),
                  padx=12, pady=8, cursor="hand2").pack(side="left", padx=3)

        tk.Button(row, text="🚀 DEPLOY", command=self.deploy,
                  bg=ACCENT, fg="#000000", activebackground="#00cc66",
                  activeforeground="#000000", relief="flat",
                  font=("Consolas", 10, "bold"),
                  padx=12, pady=8, cursor="hand2").pack(side="left", padx=3)

    def _build_list(self):
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas, bg=BG)

        self.list_frame.bind("<Configure>",
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        win_id = canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    # ---------------- ACTIONS ----------------
    def choose_file(self):
        path = filedialog.askopenfilename(title="Python file choose koro",
                                          filetypes=[("Python files", "*.py")])
        if path:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, path)

    def deploy(self):
        path = self.file_entry.get().strip()
        if not path:
            return messagebox.showwarning("Warning", "Age file choose koro!")
        if not os.path.isfile(path):
            return messagebox.showerror("Error", "File paoa gelo na!")
        if not path.endswith(".py"):
            return messagebox.showerror("Error", "Sudhu .py file deploy kora jabe!")
        if path in self.bots:
            return messagebox.showinfo("Info", "Ei file already deploy hoyeche!")
        self.file_entry.delete(0, "end")
        self._add_bot_card(path)

    def _add_bot_card(self, path):
        card = tk.Frame(self.list_frame, bg=CARD_BG)
        card.pack(fill="x", pady=6)

        inner = tk.Frame(card, bg=CARD_BG)
        inner.pack(fill="x", padx=15, pady=12)

        # --- LED (click korle jolbe) ---
        led = tk.Canvas(inner, width=22, height=22, bg=CARD_BG, highlightthickness=0)
        led.pack(side="left", padx=(0, 12))
        circle = led.create_oval(3, 3, 19, 19, fill=OFF, outline="#333333", width=1)

        info = tk.Frame(inner, bg=CARD_BG)
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info, text=os.path.basename(path), bg=CARD_BG, fg=FG,
                 font=("Consolas", 11, "bold"), anchor="w").pack(anchor="w")
        status = tk.Label(info, text="● STOPPED", bg=CARD_BG, fg="#555555",
                          font=("Consolas", 9), anchor="w")
        status.pack(anchor="w")

        btns = tk.Frame(inner, bg=CARD_BG)
        btns.pack(side="right")

        tk.Button(btns, text="▶ START", command=lambda p=path: self.start_bot(p),
                  bg="#0d3d0d", fg=ACCENT, activebackground=ACCENT,
                  activeforeground="#000000", relief="flat",
                  font=("Consolas", 9, "bold"), padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=3)

        tk.Button(btns, text="■ KILL", command=lambda p=path: self.kill_bot(p),
                  bg="#3d0d0d", fg="#ff5555", activebackground="#ff5555",
                  activeforeground="#000000", relief="flat",
                  font=("Consolas", 9, "bold"), padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=3)

        tk.Button(btns, text="🗑 DELETE", command=lambda p=path: self.delete_bot(p),
                  bg="#2a2a2a", fg="#cccccc", activebackground="#ff3333",
                  activeforeground="#ffffff", relief="flat",
                  font=("Consolas", 9, "bold"), padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=3)

        self.bots[path] = {
            "card": card, "led": led, "circle": circle,
            "status": status, "proc": None, "running": False,
        }

    # --- START / KILL / DELETE ---
    def start_bot(self, path):
        bot = self.bots.get(path)
        if not bot:
            return
        if bot["running"]:
            return messagebox.showinfo("Info", "Bot already running!")
        try:
            proc = subprocess.Popen(
                [sys.executable, "-u", path],
                cwd=os.path.dirname(path) or "."
            )
            bot["proc"] = proc
            bot["running"] = True
            self._update_led(path, True)
            self._monitor(path)
        except Exception as e:
            messagebox.showerror("Error", f"Start holo na: {e}")

    def _monitor(self, path):
        bot = self.bots.get(path)
        if not bot or not bot["proc"]:
            return
        if bot["proc"].poll() is not None:      # process shesh
            bot["running"] = False
            bot["proc"] = None
            self._update_led(path, False)
            return
        self.root.after(1000, lambda: self._monitor(path))

    def kill_bot(self, path):
        bot = self.bots.get(path)
        if not bot:
            return
        if not bot["running"] or not bot["proc"]:
            return messagebox.showinfo("Info", "Bot choltese na!")
        try:
            bot["proc"].terminate()
            try:
                bot["proc"].wait(timeout=3)
            except subprocess.TimeoutExpired:
                bot["proc"].kill()
        except Exception:
            pass
        bot["running"] = False
        bot["proc"] = None
        self._update_led(path, False)

    def delete_bot(self, path):
        bot = self.bots.get(path)
        if not bot:
            return
        if not messagebox.askyesno("Confirm",
                                   f"{os.path.basename(path)} delete korbe?\n"
                                   f"(Panel theke + asol file o delete hobe)"):
            return
        if bot["running"]:
            self.kill_bot(path)
        bot["card"].destroy()
        del self.bots[path]
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception as e:
            messagebox.showerror("Error", f"File delete holo na: {e}")

    # --- LED update ---
    def _update_led(self, path, on):
        bot = self.bots.get(path)
        if not bot:
            return
        if on:
            bot["led"].itemconfig(bot["circle"], fill=ACCENT, outline=ACCENT)
            bot["status"].config(text="● RUNNING", fg=ACCENT)
        else:
            bot["led"].itemconfig(bot["circle"], fill=OFF, outline="#333333")
            bot["status"].config(text="● STOPPED", fg="#555555")

    # --- window close: sob bot bondho ---
    def on_close(self):
        for p in list(self.bots):
            if self.bots[p]["running"]:
                self.kill_bot(p)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = BotPanel(root)
    root.mainloop()
