#!/usr/bin/env python3
# money_mission.py — Windows system tray version
# Requires: pip install pystray pillow keyboard
# Run: python money_mission.py

import json
import os
import sys
import csv
import shutil
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk, filedialog
from datetime import datetime, date, timedelta
from collections import defaultdict

import pystray
import pystray._win32
from PIL import Image, ImageDraw, ImageFont

try:
    import keyboard as kb
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

try:
    from plyer import notification as plyer_notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

# ── SUAS METAS INICIAIS ──────────────────────────────────────────────────────
DEFAULT_GOALS = [
    {"name": "Missão Principal", "amount": 25000,
     "start_date": "2026-01-01", "end_date": "2026-12-31"},
]

DEFAULT_CATEGORIES = ["Freelance", "Salário", "Investimento", "Venda", "Outro"]
HOTKEY = "ctrl+shift+m"
BACKUP_INTERVAL_MIN = 30
REMINDER_INTERVAL_MIN = 120
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# When running as .exe, PyInstaller extracts bundled files to _MEIPASS
BUNDLE_DIR = getattr(sys, '_MEIPASS', SCRIPT_DIR)
DATA_FILE = os.path.join(SCRIPT_DIR, "money_mission_data.json")
BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups")
ICON_FILE = os.path.join(BUNDLE_DIR, "icon.png")
ICO_FILE = os.path.join(BUNDLE_DIR, "money_mission.ico")

# ── Themes ───────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "BG": "#12121a", "BG2": "#181825", "BG_CARD": "#1c1c2e",
        "BG_HOVER": "#252538", "BG_INPUT": "#16162a", "BORDER": "#2e2e42",
        "FG": "#f0f0f5", "FG2": "#c8c8d8", "DIMMED": "#6b6b80",
        "ACCENT": "#34d399", "ACCENT2": "#38bdf8", "YELLOW": "#fbbf24",
        "RED": "#f87171", "RED_DIM": "#2a1420", "BLUE_DIM": "#0a1830",
        "GREEN_DIM": "#0a2818", "CHART_FILL": "#0a2818", "BAR_BG": "#1a1a2e",
        "GRID": "#1a1a2e",
    },
    "light": {
        "BG": "#f0f8f4", "BG2": "#e5f0ea", "BG_CARD": "#ffffff",
        "BG_HOVER": "#d8ece0", "BG_INPUT": "#e8f4ec", "BORDER": "#b8d4c4",
        "FG": "#0a2e1f", "FG2": "#1a4535", "DIMMED": "#508070",
        "ACCENT": "#34d399", "ACCENT2": "#38bdf8", "YELLOW": "#b08800",
        "RED": "#d32f2f", "RED_DIM": "#fce8e8", "BLUE_DIM": "#e0f4f8",
        "GREEN_DIM": "#d0f0e0", "CHART_FILL": "#d0f0e0", "BAR_BG": "#c8dcd0",
        "GRID": "#c8dcd0",
    },
}

T = THEMES["dark"]  # active theme reference


def t(key):
    return T[key]


# ── Data helpers ──────────────────────────────────────────────────────────────
def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"entries": [], "goal_assignments": {}, "goals": DEFAULT_GOALS,
                "categories": DEFAULT_CATEGORIES, "settings": {"theme": "dark"}}
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        data = {"entries": data, "goal_assignments": {}, "goals": DEFAULT_GOALS,
                "categories": DEFAULT_CATEGORIES, "settings": {"theme": "dark"}}
    data.setdefault("goals", DEFAULT_GOALS)
    data.setdefault("categories", DEFAULT_CATEGORIES)
    data.setdefault("settings", {"theme": "dark"})
    data.setdefault("goal_assignments", {})
    data.setdefault("fixed_shortcuts", [])
    data.setdefault("category_rules", {})
    data.setdefault("reflections", [])
    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_goals(data):
    out = []
    for g in data.get("goals", DEFAULT_GOALS):
        out.append({
            "name": g["name"], "amount": g["amount"],
            "start_date": date.fromisoformat(g["start_date"]) if isinstance(g["start_date"], str) else g["start_date"],
            "end_date": date.fromisoformat(g["end_date"]) if isinstance(g["end_date"], str) else g["end_date"],
        })
    return out


def entries_for_goal(data, goal_name):
    goals = get_goals(data)
    default = goals[0]["name"] if goals else ""
    asgn = data.get("goal_assignments", {})
    return [e for i, e in enumerate(data["entries"]) if asgn.get(str(i), default) == goal_name]


def total_sum(entries):
    return sum(e["amount"] for e in entries)


def today_sum(entries):
    td = date.today().isoformat()
    return sum(e["amount"] for e in entries if e["timestamp"].startswith(td))


def days_left(goal):
    return max((goal["end_date"] - date.today()).days, 0)


def days_elapsed(goal):
    return max((date.today() - goal["start_date"]).days, 1)


def current_pace(total, goal):
    return total / days_elapsed(goal)


def pct(total, goal):
    return min(total / goal["amount"], 1.0) if goal["amount"] > 0 else 0


def pct_label(total, goal):
    return f"{int(pct(total, goal) * 100)}%"


# ── Gamification ──────────────────────────────────────────────────────────────
LEVELS = [
    (0, "Iniciante", "#7a8a95"),
    (50, "Focado", "#00b8d4"),
    (150, "Dedicado", "#00d47e"),
    (350, "Imparável", "#f0c040"),
    (700, "Lenda", "#ff6b6b"),
]

MEDALS = [
    ("first_entry", "Primeira Receita", "Registrou sua primeira receita", "💰"),
    ("streak_3", "3 Dias Seguidos", "Bateu a meta 3 dias seguidos", "🔥"),
    ("streak_7", "Semana Perfeita", "Bateu a meta 7 dias seguidos", "⭐"),
    ("streak_30", "Mês Imparável", "Bateu a meta 30 dias seguidos", "👑"),
    ("pct_25", "25% da Missão", "Atingiu 25% da meta", "🎯"),
    ("pct_50", "Metade do Caminho", "Atingiu 50% da meta", "🚀"),
    ("pct_75", "Quase Lá", "Atingiu 75% da meta", "💎"),
    ("pct_100", "Missão Completa!", "Atingiu 100% da meta", "🏆"),
    ("entries_10", "10 Registros", "Fez 10 registros", "📝"),
    ("entries_50", "50 Registros", "Fez 50 registros", "📊"),
]

MILESTONES = [
    # (id, name, icon, type, threshold)
    ("val_100", "Primeiro R$100", "💵", "value", 100),
    ("val_500", "Primeiro R$500", "💰", "value", 500),
    ("val_1000", "Primeiro R$1.000", "🤑", "value", 1000),
    ("val_5000", "Primeiro R$5.000", "💎", "value", 5000),
    ("val_10000", "Primeiro R$10.000", "👑", "value", 10000),
    ("week_complete", "Primeira semana completa", "📅", "streak", 7),
    ("month_above", "Primeiro mes acima da meta", "🏅", "month_above", 1),
    ("3months_above", "3 meses seguidos acima da meta", "🏆", "month_above", 3),
    ("days_7", "7 dias usando o app", "📱", "usage_days", 7),
    ("days_30", "30 dias usando o app", "⭐", "usage_days", 30),
    ("entries_100", "100 registros", "📊", "entries", 100),
]

CSV_PARSERS = {
    "nubank": {
        "encoding": "utf-8",
        "date_col": "date",
        "desc_col": "title",
        "amount_col": "amount",
        "date_format": "%Y-%m-%d",
    },
    "banco_do_brasil": {
        "encoding": "latin-1",
        "date_col": "Data",
        "desc_col": "Histórico",
        "amount_col": "Valor",
        "date_format": "%d/%m/%Y",
        "separator": ";",
    },
    "picpay": {
        "encoding": "utf-8",
        "date_col": "Data",
        "desc_col": "Descrição",
        "amount_col": "Valor",
        "date_format": "%d/%m/%Y",
    },
    "bradesco": {
        "encoding": "latin-1",
        "date_col": "Data",
        "desc_col": "Histórico",
        "amount_col": "Valor",
        "date_format": "%d/%m/%Y",
        "separator": ";",
    },
}

DEFAULT_CATEGORY_KEYWORDS = {
    "salario": "Salário", "pagamento": "Salário",
    "pix recebido": "Freelance", "freelance": "Freelance",
    "investimento": "Investimento", "rendimento": "Investimento",
    "mercado": "Outro", "farmacia": "Outro", "uber": "Outro",
    "transferencia": "Outro",
}


def calc_gamification(data, goal):
    entries = data.get("entries", [])
    revenue_entries = [e for e in entries if e["amount"] > 0]
    total = sum(e["amount"] for e in revenue_entries)
    goal_amt = goal["amount"]
    progress = total / goal_amt if goal_amt > 0 else 0

    # XP: 10 per entry + 5 per day with entry + streak bonuses
    days_with_entries = set()
    for e in revenue_entries:
        days_with_entries.add(e["timestamp"][:10])
    xp = len(revenue_entries) * 10 + len(days_with_entries) * 5

    # Streak
    today = date.today()
    streak = 0
    remaining = max(goal_amt - total, 0)
    goal_obj = get_goals(data)
    g = goal_obj[0] if goal_obj else goal
    dl = max((g["end_date"] - today).days, 1)
    daily_needed = remaining / dl if dl > 0 else 0

    check_date = today
    while True:
        day_str = check_date.isoformat()
        day_total = sum(e["amount"] for e in revenue_entries if e["timestamp"][:10] == day_str)
        if day_total >= daily_needed and daily_needed > 0:
            streak += 1
            xp += 2  # streak bonus
            check_date -= timedelta(days=1)
        else:
            break

    # Level
    level_name = LEVELS[0][1]
    level_color = LEVELS[0][2]
    next_xp = LEVELS[1][0] if len(LEVELS) > 1 else xp
    for i, (req, name, color) in enumerate(LEVELS):
        if xp >= req:
            level_name = name
            level_color = color
            next_xp = LEVELS[i + 1][0] if i + 1 < len(LEVELS) else xp
    level_progress = (xp - [r for r, _, _ in LEVELS if xp >= r][-1]) / max(next_xp - [r for r, _, _ in LEVELS if xp >= r][-1], 1)

    # Medals earned
    earned = []
    if len(revenue_entries) >= 1:
        earned.append("first_entry")
    if streak >= 3:
        earned.append("streak_3")
    if streak >= 7:
        earned.append("streak_7")
    if streak >= 30:
        earned.append("streak_30")
    if progress >= 0.25:
        earned.append("pct_25")
    if progress >= 0.50:
        earned.append("pct_50")
    if progress >= 0.75:
        earned.append("pct_75")
    if progress >= 1.0:
        earned.append("pct_100")
    if len(revenue_entries) >= 10:
        earned.append("entries_10")
    if len(revenue_entries) >= 50:
        earned.append("entries_50")

    # Is behind today?
    today_rev = sum(e["amount"] for e in revenue_entries if e["timestamp"][:10] == today.isoformat())
    is_behind = today_rev < daily_needed and daily_needed > 0

    return {
        "xp": xp, "level": level_name, "level_color": level_color,
        "level_progress": min(level_progress, 1.0), "next_xp": next_xp,
        "streak": streak, "earned": earned, "is_behind": is_behind,
    }


def do_backup(data):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(BACKUP_DIR, f"backup_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Keep only last 20 backups
    files = sorted([os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".json")])
    for old in files[:-20]:
        os.remove(old)


# ── Icon ──────────────────────────────────────────────────────────────────────
def icon_color(progress):
    if progress >= 0.75:
        return (0, 212, 126)     # verde neon
    elif progress >= 0.40:
        return (240, 192, 64)    # amarelo
    return (255, 107, 107)       # vermelho


def create_icon_image(progress=0.0):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 2, size - 2], fill=(10, 10, 15))
    c = icon_color(progress)
    if progress > 0:
        draw.arc([4, 4, size - 4, size - 4], -90, -90 + int(360 * progress), fill=c, width=5)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    bb = draw.textbbox((0, 0), "$", font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((size - w) / 2, (size - h) / 2 - bb[1]), "$", fill=c, font=font)
    return img


# ── Window icon helper ────────────────────────────────────────────────────────
def set_window_icon(win):
    """Apply custom icon to a tkinter window."""
    try:
        if os.path.exists(ICO_FILE):
            win.iconbitmap(ICO_FILE)
        elif os.path.exists(ICON_FILE):
            icon_img = tk.PhotoImage(file=ICON_FILE)
            win.iconphoto(True, icon_img)
            win._icon_ref = icon_img
    except Exception:
        pass


def style_titlebar(win):
    """Apply dark/light title bar color to a tkinter window."""
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        if not hwnd:
            hwnd = ctypes.windll.user32.FindWindowW(None, win.title())
        if not hwnd:
            return
        is_dark = 1 if T["BG"] == "#12121a" else 0
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(is_dark)), 4)
        bg_hex = T["BG"].lstrip("#")
        r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
        cr = ctypes.c_int(r | (g << 8) | (b << 16))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(cr), 4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(cr), 4)
    except Exception:
        pass


# ── Custom tray icon (intercept right click) ─────────────────────────────────
class CustomIcon(pystray._win32.Icon):
    def __init__(self, *args, on_any_click=None, on_double_click=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_any_click = on_any_click
        self._on_double_click = on_double_click
        self._click_timer = None
        self._got_double = False
        self._click_pos = (0, 0)

    def _capture_mouse(self):
        try:
            import ctypes
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            self._click_pos = (pt.x, pt.y)
        except Exception:
            pass

    def _on_notify(self, wparam, lparam):
        # WM_LBUTTONDBLCLK = 0x0203
        if lparam == 0x0203:
            self._got_double = True
            if self._click_timer:
                self._click_timer.cancel()
                self._click_timer = None
            if self._on_double_click:
                self._on_double_click()
            return
        # WM_LBUTTONUP = 0x0202 — delay to check for double click
        if lparam == 0x0202 and self._on_any_click:
            self._got_double = False
            self._capture_mouse()  # capture NOW
            if self._click_timer:
                self._click_timer.cancel()
            self._click_timer = threading.Timer(0.3, self._delayed_click)
            self._click_timer.start()
            return
        # WM_RBUTTONUP = 0x0205 — right click, immediate
        if lparam == 0x0205 and self._on_any_click:
            self._capture_mouse()
            self._on_any_click()
            return
        super()._on_notify(wparam, lparam)

    def _delayed_click(self):
        if not self._got_double and self._on_any_click:
            self._on_any_click()
        self._click_timer = None


# ── App ───────────────────────────────────────────────────────────────────────
class Missionfy:
    def __init__(self):
        self.data = load_data()
        self.icon = None
        self.dashboard_window = None
        self._apply_theme(self.data.get("settings", {}).get("theme", "dark"))

    def _apply_theme(self, name):
        global T
        T = THEMES.get(name, THEMES["dark"])
        self.data.setdefault("settings", {})["theme"] = name

    def _goals(self):
        return get_goals(self.data)

    def _main_goal(self):
        g = self._goals()
        return g[0] if g else {"name": "Meta", "amount": 1, "start_date": date.today(), "end_date": date.today()}

    def _main_total(self):
        return total_sum(entries_for_goal(self.data, self._main_goal()["name"]))

    def _main_progress(self):
        return pct(self._main_total(), self._main_goal())

    def _build_menu(self):
        # Menu exists only as fallback — both clicks are intercepted by CustomIcon
        return pystray.Menu(
            pystray.MenuItem("Sair", self._on_quit),
        )

    def _update_icon(self):
        if self.icon:
            self.icon.icon = create_icon_image(self._main_progress())
            self.icon.title = f"Missionfy — {pct_label(self._main_total(), self._main_goal())}"
            self.icon.menu = self._build_menu()

    # ── Shortcuts ──────────────────────────────────────────────────────────────
    def _get_shortcuts(self):
        """Return up to 4 shortcuts: pinned + auto-detected from most frequent entries."""
        fixed = self.data.get("fixed_shortcuts", [])
        if len(fixed) >= 4:
            return fixed[:4]

        # Auto: analyze last 30 positive entries
        entries = [e for e in self.data["entries"] if e["amount"] > 0][-30:]
        freq = {}
        for e in entries:
            key = f"{e.get('description', '')}_{e['amount']}"
            if key not in freq:
                freq[key] = {"count": 0, "amount": e["amount"],
                             "description": e.get("description", ""),
                             "category": e.get("category", "Outro")}
            freq[key]["count"] += 1

        auto = sorted(freq.values(), key=lambda x: -x["count"])
        auto = [s for s in auto if s["count"] >= 2]  # minimum 2 occurrences

        # Combine pinned + auto, no duplicates
        fixed_descs = {s["description"] for s in fixed}
        combined = list(fixed)
        for s in auto:
            if s["description"] not in fixed_descs and len(combined) < 4:
                combined.append(s)

        return combined[:4]

    # ── Milestones ─────────────────────────────────────────────────────────────
    def _get_earned_milestones(self):
        """Return list of (icon, name) tuples for earned milestones."""
        entries = self.data.get("entries", [])
        revenue = [e for e in entries if e["amount"] > 0]
        total_rev = sum(e["amount"] for e in revenue)
        gm = calc_gamification(self.data, self._main_goal())
        usage_days = len(set(e["timestamp"][:10] for e in entries))

        earned = []
        for mid, name, icon, mtype, val in MILESTONES:
            unlocked = False
            if mtype == "value":
                unlocked = total_rev >= val
            elif mtype == "streak":
                unlocked = gm["streak"] >= val
            elif mtype == "entries":
                unlocked = len(revenue) >= val
            elif mtype == "usage_days":
                unlocked = usage_days >= val
            elif mtype == "month_above":
                unlocked = False  # simplified - would need monthly data
            if unlocked:
                earned.append((icon, name))
        return earned

    # ── Custom popup menu ─────────────────────────────────────────────────────
    def _show_tray_popup(self, icon, item=None):
        # Use position captured at click time by CustomIcon
        cx, cy = self.icon._click_pos if self.icon else (0, 0)
        threading.Thread(target=lambda: self._create_tray_popup(cx, cy), daemon=True).start()

    def _create_tray_popup(self, click_x=None, click_y=None):
        popup = tk.Tk()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=t("BORDER"))

        # Position: always near taskbar, anchored to click X
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        cx = click_x if click_x is not None else popup.winfo_pointerx()

        # Outer border glow
        inner = tk.Frame(popup, bg=t("BG"))
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Gather data ──────────────────────────────────────────────────
        goal = self._main_goal()
        progress = self._main_progress()
        gamification = calc_gamification(self.data, goal)
        streak = gamification.get("streak", 0)

        gt = self._main_total()
        goal_amt = goal["amount"]
        remaining = max(goal_amt - gt, 0)
        dl = max(days_left(goal), 1)
        daily_needed = remaining / dl if dl > 0 else 0

        today = date.today()
        revenue_entries = [e for e in self.data.get("entries", []) if e["amount"] > 0]
        today_rev = sum(e["amount"] for e in revenue_entries if e["timestamp"][:10] == today.isoformat())

        # ── 1. Header (BG_CARD) ──────────────────────────────────────────
        hdr = tk.Frame(inner, bg=t("BG_CARD"), padx=16, pady=12)
        hdr.pack(fill="x")

        # Brand row: icon + "Missionfy" + streak
        brand_row = tk.Frame(hdr, bg=t("BG_CARD"))
        brand_row.pack(fill="x")

        brand_left = tk.Frame(brand_row, bg=t("BG_CARD"))
        brand_left.pack(side="left")
        try:
            if os.path.exists(ICON_FILE):
                from PIL import ImageTk
                ico = Image.open(ICON_FILE).resize((22, 22), Image.LANCZOS)
                photo = ImageTk.PhotoImage(ico)
                icon_lbl = tk.Label(brand_left, image=photo, bg=t("BG_CARD"), anchor="center")
                icon_lbl.image = photo
                icon_lbl.pack(side="left", padx=(0, 6), pady=0)
        except Exception:
            pass
        tk.Label(brand_left, text="Missionfy", font=(FONT, 12, "bold"),
                 bg=t("BG_CARD"), fg=t("FG"), anchor="center").pack(side="left", pady=0)

        if streak > 0:
            tk.Label(brand_row, text=f"\U0001f525{streak}", font=(FONT, 12, "bold"),
                     bg=t("BG_CARD"), fg=t("YELLOW")).pack(side="right")

        # Smart message
        if today_rev >= daily_needed and daily_needed > 0:
            smart_text = "Meta do dia batida!"
            smart_color = t("ACCENT")
        elif daily_needed > 0:
            faltam = daily_needed - today_rev
            smart_text = f"Faltam R${faltam:,.2f} hoje"
            smart_color = t("YELLOW")
        else:
            smart_text = f"{int(progress * 100)}% da meta"
            smart_color = t("ACCENT")

        tk.Label(hdr, text=smart_text, font=(FONT, 13, "bold"),
                 bg=t("BG_CARD"), fg=smart_color, anchor="w").pack(fill="x", pady=(6, 4))

        # Progress bar of main goal
        bar_f = tk.Frame(hdr, bg=t("BAR_BG"), height=6)
        bar_f.pack(fill="x", pady=(0, 2))
        bar_f.pack_propagate(False)
        bar_color = t("ACCENT") if progress >= 0.75 else (t("YELLOW") if progress >= 0.4 else t("RED"))
        if progress > 0:
            tk.Frame(bar_f, bg=bar_color, height=6).place(relx=0, rely=0, relwidth=min(progress, 1.0), relheight=1.0)

        # ── 2. Quick register section ────────────────────────────────────
        tk.Frame(inner, bg=t("BORDER"), height=1).pack(fill="x", padx=12, pady=6)

        reg_frame = tk.Frame(inner, bg=t("BG"), padx=16)
        reg_frame.pack(fill="x")

        # Tipo toggle
        tipo_var = tk.StringVar(value="receita")
        toggle_frame = tk.Frame(reg_frame, bg=t("BG"))
        toggle_frame.pack(fill="x", pady=(0, 6))

        def rebuild_toggle():
            for w in toggle_frame.winfo_children():
                w.destroy()
            current = tipo_var.get()
            # + Receita
            r_bg = t("ACCENT") if current == "receita" else t("BG_HOVER")
            r_fg = t("BG") if current == "receita" else t("FG2")
            lbl_r = tk.Label(toggle_frame, text="+ Receita", font=(FONT, 11, "bold"),
                             bg=r_bg, fg=r_fg, padx=12, pady=4, cursor="hand2")
            lbl_r.pack(side="left", padx=(0, 4))
            lbl_r.bind("<Button-1>", lambda e: (tipo_var.set("receita"), rebuild_toggle()))
            # - Despesa
            d_bg = t("YELLOW") if current == "despesa" else t("BG_HOVER")
            d_fg = t("BG") if current == "despesa" else t("FG2")
            lbl_d = tk.Label(toggle_frame, text="- Despesa", font=(FONT, 11, "bold"),
                             bg=d_bg, fg=d_fg, padx=12, pady=4, cursor="hand2")
            lbl_d.pack(side="left")
            lbl_d.bind("<Button-1>", lambda e: (tipo_var.set("despesa"), rebuild_toggle()))

        rebuild_toggle()

        # Entry field for amount
        val_entry = tk.Entry(reg_frame, font=(FONT, 14), bg=t("BG_INPUT"), fg=t("DIMMED"),
                             insertbackground=t("FG"), relief="flat",
                             highlightbackground=t("BORDER"), highlightthickness=1)
        val_entry.insert(0, "Valor em R$")
        val_entry.pack(fill="x", ipady=5, pady=(0, 6))

        def on_entry_focus(e):
            if val_entry.get() == "Valor em R$":
                val_entry.delete(0, "end")
                val_entry.configure(fg=t("FG"))

        def on_entry_blur(e):
            if not val_entry.get().strip():
                val_entry.insert(0, "Valor em R$")
                val_entry.configure(fg=t("DIMMED"))

        val_entry.bind("<FocusIn>", on_entry_focus)
        val_entry.bind("<FocusOut>", on_entry_blur)

        # Quick save function
        def quick_save(e=None):
            amt_str = val_entry.get().strip()
            if not amt_str or amt_str == "Valor em R$":
                return
            try:
                amount = float(amt_str.replace("R$", "").replace("$", "").replace(",", "."))
                if tipo_var.get() == "despesa":
                    amount = -abs(amount)
            except ValueError:
                return
            entry = {
                "amount": amount, "description": "Registro rapido",
                "category": self.data.get("categories", DEFAULT_CATEGORIES)[0],
                "type": tipo_var.get(), "timestamp": datetime.now().isoformat(),
            }
            self.data["entries"].append(entry)
            goals = self._goals()
            if goals:
                self.data["goal_assignments"][str(len(self.data["entries"]) - 1)] = goals[0]["name"]
            save_data(self.data)
            self._update_icon()
            self._try_refresh()
            popup.destroy()

        val_entry.bind("<Return>", quick_save)

        # Shortcut buttons (up to 4)
        try:
            shortcuts = self._get_shortcuts()
            if shortcuts:
                sc_frame = tk.Frame(reg_frame, bg=t("BG"))
                sc_frame.pack(fill="x", pady=(0, 4))
                for sc in shortcuts[:4]:
                    sc_text = f"{sc['description']} R${sc['amount']}"

                    def make_sc_click(s=sc):
                        def on_click(e=None):
                            amt = s["amount"]
                            if s.get("type", "receita") == "despesa":
                                amt = -abs(amt)
                            entry = {
                                "amount": amt, "description": s["description"],
                                "category": s.get("category", self.data.get("categories", DEFAULT_CATEGORIES)[0]),
                                "type": s.get("type", "receita"), "timestamp": datetime.now().isoformat(),
                            }
                            self.data["entries"].append(entry)
                            goals = self._goals()
                            if goals:
                                self.data["goal_assignments"][str(len(self.data["entries"]) - 1)] = goals[0]["name"]
                            save_data(self.data)
                            self._update_icon()
                            self._try_refresh()
                            popup.destroy()
                        return on_click

                    sc_btn = tk.Label(sc_frame, text=sc_text, font=(FONT, 10),
                                      bg=t("BG_HOVER"), fg=t("FG2"), padx=8, pady=3, cursor="hand2")
                    sc_btn.pack(side="left", padx=(0, 4))
                    sc_btn.bind("<Button-1>", make_sc_click(sc))
        except Exception:
            pass

        # ── 3. Actions ───────────────────────────────────────────────────
        tk.Frame(inner, bg=t("BORDER"), height=1).pack(fill="x", padx=12, pady=6)

        def make_action(icon_char, label, cmd, fg_c=None):
            fg_c = fg_c or t("FG")
            btn = tk.Frame(inner, bg=t("BG"), cursor="hand2")
            btn.pack(fill="x")

            lbl_icon = tk.Label(btn, text=icon_char, font=(FONT, 12),
                                bg=t("BG"), fg=fg_c, width=3)
            lbl_icon.pack(side="left", padx=(12, 0), pady=5)
            lbl_text = tk.Label(btn, text=label, font=(FONT, 12),
                                bg=t("BG"), fg=fg_c, anchor="w")
            lbl_text.pack(side="left", fill="x", expand=True, pady=5)

            def enter(e):
                btn.configure(bg=t("BG_HOVER"))
                lbl_icon.configure(bg=t("BG_HOVER"))
                lbl_text.configure(bg=t("BG_HOVER"))
            def leave(e):
                btn.configure(bg=t("BG"))
                lbl_icon.configure(bg=t("BG"))
                lbl_text.configure(bg=t("BG"))
            def click(e):
                popup.destroy()
                cmd(self.icon, None)

            for w in (btn, lbl_icon, lbl_text):
                w.bind("<Enter>", enter)
                w.bind("<Leave>", leave)
                w.bind("<Button-1>", click)

        make_action("\u25fb", "Ver Painel", self._on_show_dashboard, t("ACCENT2"))

        tk.Frame(inner, bg=t("BORDER"), height=1).pack(fill="x", padx=12, pady=6)

        make_action("\u2715", "Sair", self._on_quit, t("RED"))

        # ── Position: above taskbar, near click ──────────────────────────
        popup.update_idletasks()
        pw = max(popup.winfo_reqwidth(), 300)
        ph = popup.winfo_reqheight()

        # Taskbar height (~48px on most systems)
        taskbar_h = screen_h - popup.winfo_screenheight() if popup.winfo_screenheight() != screen_h else 48
        taskbar_h = max(taskbar_h, 48)

        # X: centered on click position, clamped to screen
        final_x = max(5, min(cx - pw // 2, screen_w - pw - 5))
        # Y: just above taskbar
        final_y = screen_h - taskbar_h - ph - 8
        popup.geometry(f"{pw}x{ph}+{final_x}+{final_y}")

        def close_popup(e=None):
            try:
                popup.destroy()
            except Exception:
                pass

        popup.bind("<Escape>", close_popup)
        popup.bind("<FocusOut>", close_popup)
        popup.focus_force()
        val_entry.focus_set()
        popup.mainloop()

    # ── Add revenue / expense ─────────────────────────────────────────────────
    def _on_add_revenue(self, icon, item):
        threading.Thread(target=lambda: self._add_entry_dialog("receita"), daemon=True).start()

    def _on_add_expense(self, icon, item):
        threading.Thread(target=lambda: self._add_entry_dialog("despesa"), daemon=True).start()

    def _add_entry_dialog(self, tipo="receita"):
        dlg = tk.Tk()
        dlg.title(f"Adicionar {tipo.title()}")
        dlg.configure(bg=t("BG"))
        dlg.geometry("380x420")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        set_window_icon(dlg)
        dlg.after(50, lambda: style_titlebar(dlg))

        accent = t("ACCENT") if tipo == "receita" else t("YELLOW")
        title_text = "Nova Receita" if tipo == "receita" else "Nova Despesa"
        tk.Label(dlg, text=title_text, font=(FONT, 14, "bold"),
                 bg=t("BG"), fg=accent).pack(pady=(18, 12))

        form = tk.Frame(dlg, bg=t("BG"))
        form.pack(padx=25, fill="x")

        # Valor
        tk.Label(form, text="VALOR (R$)", font=(FONT, 12), bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(0, 3))
        amount_entry = tk.Entry(form, font=(FONT, 13), bg=t("BG_INPUT"), fg=t("FG"),
                                insertbackground=t("FG"), relief="flat",
                                highlightbackground=t("BORDER"), highlightthickness=1)
        amount_entry.pack(fill="x", ipady=5)
        amount_entry.focus_set()

        # Descrição
        tk.Label(form, text="DESCRIÇÃO", font=(FONT, 12), bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(12, 3))
        desc_entry = tk.Entry(form, font=(FONT, 12), bg=t("BG_INPUT"), fg=t("FG"),
                              insertbackground=t("FG"), relief="flat",
                              highlightbackground=t("BORDER"), highlightthickness=1)
        desc_entry.pack(fill="x", ipady=4)

        # Categoria
        cats = self.data.get("categories", DEFAULT_CATEGORIES)
        tk.Label(form, text="CATEGORIA", font=(FONT, 12), bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(12, 3))
        cat_frame = tk.Frame(form, bg=t("BG"))
        cat_frame.pack(fill="x")
        cat_frame.columnconfigure(0, weight=1)
        cat_frame.columnconfigure(1, weight=1)
        cat_frame.columnconfigure(2, weight=1)
        selected_cat = tk.StringVar(value=cats[0] if cats else "Outro")

        for idx, cat in enumerate(cats):
            def make_cat_btn(c, i):
                btn = tk.Label(cat_frame, text=c, font=(FONT, 12), padx=10, pady=4, cursor="hand2",
                               bg=t("BG_HOVER"), fg=t("FG"))
                def select(e=None):
                    selected_cat.set(c)
                    for w in cat_frame.winfo_children():
                        w.configure(bg=t("BG_HOVER"), fg=t("FG"))
                    btn.configure(bg=accent, fg=t("BG"))
                btn.bind("<Button-1>", select)
                row, col = divmod(i, 3)
                btn.grid(row=row, column=col, padx=(0, 4), pady=2, sticky="ew")
                return btn
            b = make_cat_btn(cat, idx)
            if cat == cats[0]:
                b.configure(bg=accent, fg=t("BG"))

        # Meta (se houver mais de uma)
        goals = self._goals()
        selected_goal = tk.StringVar(value=goals[0]["name"] if goals else "")
        if len(goals) > 1:
            tk.Label(form, text="MISSÃO", font=(FONT, 12), bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(12, 3))
            goal_frame = tk.Frame(form, bg=t("BG"))
            goal_frame.pack(fill="x")
            for g in goals:
                def make_goal_btn(gn):
                    btn = tk.Label(goal_frame, text=gn, font=(FONT, 12), padx=10, pady=4, cursor="hand2",
                                   bg=t("BG_HOVER"), fg=t("FG"))
                    def select(e=None):
                        selected_goal.set(gn)
                        for w in goal_frame.winfo_children():
                            w.configure(bg=t("BG_HOVER"), fg=t("FG"))
                        btn.configure(bg=t("ACCENT2"), fg=t("BG"))
                    btn.bind("<Button-1>", select)
                    btn.pack(side="left", padx=(0, 4), pady=2)
                    return btn
                b = make_goal_btn(g["name"])
                if g["name"] == goals[0]["name"]:
                    b.configure(bg=t("ACCENT2"), fg=t("BG"))

        # Salvar
        def save():
            amt_str = amount_entry.get().strip()
            if not amt_str:
                return
            try:
                amount = float(amt_str.replace("R$", "").replace("$", "").replace(",", "."))
                if tipo == "despesa":
                    amount = -abs(amount)
            except ValueError:
                return

            entry = {
                "amount": amount,
                "description": desc_entry.get().strip() or "Sem descrição",
                "category": selected_cat.get(),
                "type": tipo,
                "timestamp": datetime.now().isoformat(),
            }
            self.data["entries"].append(entry)
            self.data["goal_assignments"][str(len(self.data["entries"]) - 1)] = selected_goal.get()
            save_data(self.data)
            dlg.destroy()
            self._update_icon()
            self._try_refresh()

            # Notification
            try:
                if self.icon:
                    goal = self._main_goal()
                    total = self._main_total()
                    progress_pct = int(pct(total, goal) * 100)
                    sign = "+" if amount >= 0 else ""
                    msg = f"{sign}R${amount:,.2f} registrado!\nProgresso: {progress_pct}% da meta."

                    # Milestone notifications
                    for marco in [25, 50, 75, 100]:
                        old_pct = int(pct(total - abs(amount), goal) * 100)
                        if old_pct < marco <= progress_pct:
                            msg = f"🎯 Você atingiu {marco}% da meta!\nTotal: R${total:,.2f}"
                            break

                    self.icon.notify(msg, "Missionfy")
            except Exception:
                pass

        btn_row = tk.Frame(dlg, bg=t("BG"))
        btn_row.pack(fill="x", padx=25, pady=(18, 0))

        save_btn = tk.Label(btn_row, text=f"Salvar {tipo.title()}", font=(FONT, 12),
                            bg=accent, fg=t("BG"), pady=10, cursor="hand2")
        save_btn.bind("<Button-1>", lambda e: save())
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        cancel_btn = tk.Label(btn_row, text="Cancelar", font=(FONT, 12),
                              bg=t("BG_HOVER"), fg=t("DIMMED"), pady=10, cursor="hand2")
        cancel_btn.bind("<Button-1>", lambda e: dlg.destroy())
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Enter to save
        dlg.bind("<Return>", lambda e: save())
        dlg.bind("<Escape>", lambda e: dlg.destroy())

        dlg.mainloop()

    # ── Dashboard ─────────────────────────────────────────────────────────────
    def _on_show_dashboard(self, icon, item):
        threading.Thread(target=self._show_dashboard, daemon=True).start()

    def _show_dashboard(self):
        try:
            if self.dashboard_window and self.dashboard_window.winfo_exists():
                self.dashboard_window.deiconify()
                self.dashboard_window.lift()
                return
        except Exception:
            self.dashboard_window = None

        win = tk.Tk()
        win.title("Missionfy")
        win.configure(bg=t("BG"))

        # DPI awareness — adapta a qualquer escala de tela
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # 80% da tela, centralizado
        screen_h = win.winfo_screenheight()
        screen_w = win.winfo_screenwidth()
        win_w = min(800, int(screen_w * 0.55))
        win_h = int(screen_h * 0.85)
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        win.geometry(f"{win_w}x{win_h}+{x}+{y}")
        win.resizable(True, True)
        win.minsize(550, 400)
        set_window_icon(win)
        self.dashboard_window = win

        style = ttk.Style(win)
        style.theme_use("clam")
        style.configure("TScrollbar", background=t("BG2"), troughcolor=t("BG"),
                         bordercolor=t("BG"), arrowcolor=t("DIMMED"), relief="flat")

        # X = minimizar para tray (esconder), não destruir
        win.protocol("WM_DELETE_WINDOW", self._hide_dashboard)

        self._draw_dashboard(win)
        win.after(100, lambda: self._apply_titlebar_color(win))
        win.mainloop()

    @staticmethod
    def _apply_titlebar_color(win):
        style_titlebar(win)

    def _hide_dashboard(self):
        if self.dashboard_window:
            self.dashboard_window.withdraw()

    def _try_refresh(self):
        try:
            if self.dashboard_window and self.dashboard_window.winfo_exists():
                self.dashboard_window.after(100, self._refresh_dashboard)
        except Exception:
            pass

    def _refresh_dashboard(self, keep_scroll=False):
        try:
            if not self.dashboard_window or not self.dashboard_window.winfo_exists():
                return
        except Exception:
            self.dashboard_window = None
            return
        # Save scroll position
        scroll_pos = None
        if keep_scroll:
            for w in self.dashboard_window.winfo_children():
                for c in w.winfo_children():
                    if isinstance(c, tk.Canvas):
                        scroll_pos = c.yview()[0]
                        break
        for w in self.dashboard_window.winfo_children():
            w.destroy()
        self.dashboard_window.configure(bg=t("BG"))
        self._draw_dashboard(self.dashboard_window)
        # Restore scroll position
        if scroll_pos is not None:
            def restore():
                for w in self.dashboard_window.winfo_children():
                    for c in w.winfo_children():
                        if isinstance(c, tk.Canvas):
                            c.yview_moveto(scroll_pos)
                            return
            self.dashboard_window.after(150, restore)

    # ── Draw dashboard ────────────────────────────────────────────────────────
    def _draw_dashboard(self, win):
        PAD = 24

        main = tk.Frame(win, bg=t("BG"))
        main.pack(fill="both", expand=True)

        # ── Header (always visible) ──────────────────────────────────────────
        hdr = tk.Frame(main, bg=t("BG"))
        hdr.pack(fill="x", padx=PAD, pady=(12, 0))

        try:
            if os.path.exists(ICON_FILE):
                from PIL import ImageTk
                ico = Image.open(ICON_FILE).resize((36, 36), Image.LANCZOS)
                photo = ImageTk.PhotoImage(ico)
                icon_lbl = tk.Label(hdr, image=photo, bg=t("BG"))
                icon_lbl.image = photo
                icon_lbl.pack(side="left", padx=(0, 10))
        except Exception:
            pass

        title_f = tk.Frame(hdr, bg=t("BG"))
        title_f.pack(side="left")
        tr = tk.Frame(title_f, bg=t("BG"))
        tr.pack(anchor="w")
        tk.Label(tr, text="Missionfy", font=(FONT, 16, "bold"),
                 bg=t("BG"), fg=t("FG")).pack(side="left")
        dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        hoje = date.today()
        tk.Label(title_f, text=f"{dias[hoje.weekday()]}, {hoje.day} de {meses[hoje.month]} de {hoje.year}",
                 font=(FONT, 9), bg=t("BG"), fg=t("DIMMED")).pack(anchor="w")

        hdr_btns = tk.Frame(hdr, bg=t("BG"))
        hdr_btns.pack(side="right")
        self._btn(hdr_btns, "Exportar", self._export_csv, t("GREEN_DIM"), t("ACCENT"), 10).pack(side="left", padx=3)

        tk.Frame(main, bg=t("BORDER"), height=1).pack(fill="x", padx=PAD, pady=(8, 0))

        # ── Fixed footer (outside scroll, packed first to reserve space) ─────
        footer = tk.Frame(main, bg=t("BG2"))
        footer.pack(fill="x", side="bottom")
        tk.Frame(footer, bg=t("BORDER"), height=1).pack(fill="x")
        footer_inner = tk.Frame(footer, bg=t("BG2"))
        footer_inner.pack(fill="x", padx=PAD, pady=10)

        self._btn(footer_inner, "Registrar", lambda: self._on_add_revenue(None, None),
                  t("ACCENT"), t("BG"), 11).pack(side="left", padx=(0, 8))
        self._btn(footer_inner, "Importar CSV", self._show_csv_import,
                  t("BG_HOVER"), t("FG"), 11).pack(side="left", padx=(0, 8))
        self._btn(footer_inner, "Config", self._show_config_window,
                  t("BG_HOVER"), t("FG"), 11).pack(side="left", padx=(0, 8))

        # ── Scrollable content area ──────────────────────────────────────────
        content_outer = tk.Frame(main, bg=t("BG"))
        content_outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(content_outer, bg=t("BG"), highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(content_outer, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=t("BG"))

        cf = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _update_scroll(e=None):
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox:
                return
            ch = bbox[3] - bbox[1]
            cvh = canvas.winfo_height()
            if ch > cvh:
                canvas.configure(scrollregion=(0, 0, bbox[2], ch))
                scrollbar.pack(side="right", fill="y")
            else:
                canvas.configure(scrollregion=(0, 0, bbox[2], cvh))
                scrollbar.pack_forget()

        frame.bind("<Configure>", _update_scroll)
        canvas.bind("<Configure>", lambda e: (canvas.itemconfig(cf, width=e.width), _update_scroll()))
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        win.after(100, lambda: (canvas.yview_moveto(0), _update_scroll()))

        # ── Sections ─────────────────────────────────────────────────────────
        self._draw_seu_dia(frame)
        self._draw_sua_semana(frame)
        self._draw_sua_jornada(frame)
        self._draw_suas_metas(frame)

        tk.Frame(frame, bg=t("BG"), height=10).pack()

    # ── Seção: Seu Dia ────────────────────────────────────────────────────────
    def _draw_seu_dia(self, parent):
        PAD = 24
        goal = self._main_goal()
        goals = self._goals()
        total = self._main_total()
        remaining = max(goal["amount"] - total, 0)
        dl = days_left(goal)
        daily_needed = remaining / dl if dl > 0 else 0
        ents = entries_for_goal(self.data, goal["name"])
        today_rev = sum(e["amount"] for e in ents if e["amount"] > 0
                        and e["timestamp"][:10] == date.today().isoformat())
        day_progress = min(today_rev / daily_needed, 1.0) if daily_needed > 0 else 0

        sec = tk.Frame(parent, bg=t("BG"))
        sec.pack(fill="x", padx=PAD, pady=(16, 4))
        tk.Label(sec, text="SEU DIA", font=(FONT, 10, "bold"),
                 bg=t("BG"), fg=t("DIMMED")).pack(anchor="w")

        # Status message
        if not goals:
            msg = "Nenhuma meta ativa"
            msg_color = t("DIMMED")
        elif today_rev >= daily_needed and daily_needed > 0:
            msg = "Meta do dia batida!"
            msg_color = t("ACCENT")
        elif daily_needed > 0:
            falta = max(daily_needed - today_rev, 0)
            msg = f"Faltam R${falta:,.2f} pra meta de hoje"
            msg_color = t("YELLOW")
        else:
            msg = "Nenhuma meta ativa"
            msg_color = t("DIMMED")

        tk.Label(sec, text=msg, font=(FONT, 16, "bold"),
                 bg=t("BG"), fg=msg_color).pack(anchor="w", pady=(4, 8))

        # Progress bar (height=14)
        bar_outer = tk.Frame(sec, bg=t("BAR_BG"), height=14)
        bar_outer.pack(fill="x", pady=(0, 6))
        bar_outer.pack_propagate(False)
        if day_progress > 0:
            bar_fill = tk.Frame(bar_outer, bg=t("ACCENT"), height=14)
            bar_fill.place(relx=0, rely=0, relwidth=0, relheight=1.0)
            bar_outer.after(50, lambda bf=bar_fill, p=day_progress: bf.place(relwidth=min(p, 1.0)))

        # Small text
        tk.Label(sec, text=f"R${today_rev:,.2f} de R${daily_needed:,.2f} hoje",
                 font=(FONT, 9), bg=t("BG"), fg=t("DIMMED")).pack(anchor="w")

    # ── Seção: Sua Semana ─────────────────────────────────────────────────────
    def _draw_sua_semana(self, parent):
        PAD = 24
        goal = self._main_goal()
        total = self._main_total()
        remaining = max(goal["amount"] - total, 0)
        dl = days_left(goal)
        daily_needed = remaining / dl if dl > 0 else 0
        ents = entries_for_goal(self.data, goal["name"])
        revenue_ents = [e for e in ents if e["amount"] > 0]
        gm = calc_gamification(self.data, goal)
        hoje = date.today()

        sec = tk.Frame(parent, bg=t("BG"))
        sec.pack(fill="x", padx=PAD, pady=(16, 4))

        title_row = tk.Frame(sec, bg=t("BG"))
        title_row.pack(fill="x")
        tk.Label(title_row, text="SUA SEMANA", font=(FONT, 10, "bold"),
                 bg=t("BG"), fg=t("DIMMED")).pack(side="left")
        if gm["streak"] > 0:
            tk.Label(title_row, text=f"\U0001f525 {gm['streak']} dias seguidos",
                     font=(FONT, 10), bg=t("BG"), fg=t("YELLOW")).pack(side="right")

        # Week grid (Mon-Sun)
        week_start = hoje - timedelta(days=hoje.weekday())
        day_labels = ["S", "T", "Q", "Q", "S", "S", "D"]

        grid_frame = tk.Frame(sec, bg=t("BG"))
        grid_frame.pack(fill="x", pady=(8, 0))

        for i in range(7):
            day_date = week_start + timedelta(days=i)
            day_str = day_date.isoformat()
            day_total = sum(e["amount"] for e in revenue_ents if e["timestamp"][:10] == day_str)

            is_today = day_date == hoje
            is_future = day_date > hoje
            met_target = day_total >= daily_needed and daily_needed > 0

            if met_target:
                sq_bg = t("ACCENT")
                sq_fg = t("BG")
            elif is_future:
                sq_bg = t("BG_HOVER")
                sq_fg = t("DIMMED")
            elif day_date < hoje and not met_target:
                sq_bg = t("RED_DIM")
                sq_fg = t("RED")
            else:
                sq_bg = t("BG_HOVER")
                sq_fg = t("DIMMED")

            hl_thick = 2 if is_today else 0
            hl_color = t("ACCENT") if is_today else t("BG")

            col_frame = tk.Frame(grid_frame, bg=t("BG"))
            col_frame.pack(side="left", padx=(0, 6))

            tk.Label(col_frame, text=day_labels[i], font=(FONT, 9),
                     bg=t("BG"), fg=t("DIMMED")).pack()

            sq = tk.Frame(col_frame, bg=sq_bg, width=36, height=36,
                          highlightbackground=hl_color, highlightthickness=hl_thick)
            sq.pack()
            sq.pack_propagate(False)

            if day_total > 0:
                amt_text = f"{int(day_total)}" if day_total >= 1 else f"{day_total:.0f}"
                tk.Label(sq, text=f"R${amt_text}", font=(FONT, 7),
                         bg=sq_bg, fg=sq_fg).pack(expand=True)

    # ── Seção: Sua Jornada ─────────────────────────────────────────────────────
    def _draw_sua_jornada(self, parent):
        PAD = 24
        entries = [e for e in self.data["entries"] if e["amount"] > 0]
        if not entries:
            return

        sec = tk.Frame(parent, bg=t("BG"))
        sec.pack(fill="x", padx=PAD, pady=(16, 4))
        tk.Label(sec, text="SUA JORNADA", font=(FONT, 10, "bold"),
                 bg=t("BG"), fg=t("DIMMED")).pack(anchor="w")

        # Weekly chart
        card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        card.pack(fill="x", padx=PAD, pady=(4, 0))

        cw, ch = 500, 180
        c = tk.Canvas(card, width=cw, height=ch, bg=t("BG_CARD"), highlightthickness=0)
        c.pack(padx=12, pady=12, fill="x")

        today = date.today()
        weeks = []
        for w in range(7, -1, -1):
            week_start = today - timedelta(days=today.weekday() + 7 * w)
            week_end = week_start + timedelta(days=6)
            week_total = sum(e["amount"] for e in entries
                            if week_start.isoformat() <= e["timestamp"][:10] <= week_end.isoformat())
            weeks.append({"start": week_start, "total": week_total})

        max_val = max((w["total"] for w in weeks), default=1) or 1
        pl, pr, pt, pb = 60, 12, 12, 30
        pw, ph = cw - pl - pr, ch - pt - pb

        for i, w in enumerate(weeks):
            x = pl + ((i + 0.5) / len(weeks)) * pw
            y_top = pt + ph * (1 - w["total"] / (max_val * 1.15))
            y_bot = pt + ph
            bar_w = pw / len(weeks) * 0.6

            c.create_rectangle(x - bar_w/2, y_top, x + bar_w/2, y_bot,
                              fill=t("ACCENT"), outline="")
            label = w["start"].strftime("%d/%m")
            c.create_text(x, ch - 8, text=label, fill=t("DIMMED"), font=(FONT, 7))
            if w["total"] > 0:
                c.create_text(x, y_top - 10, text=f"R${w['total']:,.0f}",
                             fill=t("FG"), font=(FONT, 7))

        # Milestones earned
        try:
            milestones = self._get_earned_milestones()
        except AttributeError:
            milestones = []

        if milestones:
            ms_frame = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
            ms_frame.pack(fill="x", padx=PAD, pady=(4, 0))
            ms_inner = tk.Frame(ms_frame, bg=t("BG_CARD"), padx=16, pady=10)
            ms_inner.pack(fill="x")
            tk.Label(ms_inner, text="MARCOS CONQUISTADOS", font=(FONT, 9, "bold"),
                     bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(0, 6))
            for icon, name in milestones:
                mf = tk.Frame(ms_inner, bg=t("BG_CARD"))
                mf.pack(fill="x", pady=2)
                tk.Label(mf, text=icon, font=(FONT, 14), bg=t("BG_CARD")).pack(side="left", padx=(0, 8))
                tk.Label(mf, text=name, font=(FONT, 11), bg=t("BG_CARD"), fg=t("FG")).pack(side="left")

        # Reflections history
        reflections = self.data.get("reflections", [])
        if reflections:
            ref_frame = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
            ref_frame.pack(fill="x", padx=PAD, pady=(4, 0))
            ref_inner = tk.Frame(ref_frame, bg=t("BG_CARD"), padx=16, pady=10)
            ref_inner.pack(fill="x")
            tk.Label(ref_inner, text="SUAS REFLEXOES", font=(FONT, 9, "bold"),
                     bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(0, 6))
            feelings_map = {"otima": "\U0001f604", "boa": "\U0001f642", "podia_ser_melhor": "\U0001f610"}
            for r in reflections[-4:]:
                rf = tk.Frame(ref_inner, bg=t("BG_CARD"))
                rf.pack(fill="x", pady=2)
                emoji = feelings_map.get(r.get("feeling", ""), "")
                tk.Label(rf, text=f"{emoji} Semana de {r['week']}", font=(FONT, 10),
                         bg=t("BG_CARD"), fg=t("FG")).pack(side="left")
                if r.get("note"):
                    tk.Label(rf, text=f"- {r['note']}", font=(FONT, 9),
                             bg=t("BG_CARD"), fg=t("DIMMED")).pack(side="left", padx=(8, 0))

        # ── 30-day calendar ──
        cal_card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        cal_card.pack(fill="x", padx=PAD, pady=(4, 0))
        cal_inner = tk.Frame(cal_card, bg=t("BG_CARD"), padx=16, pady=10)
        cal_inner.pack(fill="x")

        tk.Label(cal_inner, text="ULTIMOS 30 DIAS", font=(FONT, 9, "bold"),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(0, 8))

        goal = self._main_goal()
        rev_entries = [e for e in self.data["entries"] if e["amount"] > 0]
        total_rev = sum(e["amount"] for e in rev_entries)
        rem = max(goal["amount"] - total_rev, 0)
        dl_val = max(days_left(goal), 1)
        daily_needed = rem / dl_val

        grid = tk.Frame(cal_inner, bg=t("BG_CARD"))
        grid.pack(fill="x")

        today = date.today()
        for i in range(30):
            d = today - timedelta(days=29 - i)
            day_str = d.isoformat()
            day_total = sum(e["amount"] for e in rev_entries if e["timestamp"][:10] == day_str)

            if day_total >= daily_needed and daily_needed > 0:
                color = t("ACCENT")
            elif day_total > 0:
                color = t("YELLOW")
            else:
                color = t("BAR_BG")

            row, col = divmod(i, 10)
            sq = tk.Frame(grid, bg=color, width=20, height=20,
                          highlightbackground=t("BORDER") if d != today else t("ACCENT"),
                          highlightthickness=1 if d != today else 2)
            sq.grid(row=row, column=col, padx=2, pady=2)
            sq.grid_propagate(False)

    # ── Seção: Suas Metas ─────────────────────────────────────────────────────
    def _draw_suas_metas(self, parent):
        PAD = 24
        sec = tk.Frame(parent, bg=t("BG"))
        sec.pack(fill="x", padx=PAD, pady=(16, 4))
        tk.Label(sec, text="SUAS METAS", font=(FONT, 10, "bold"),
                 bg=t("BG"), fg=t("DIMMED")).pack(anchor="w")
        for goal in self._goals():
            self._draw_goal_card(parent, goal)

    # ── CSV Import ─────────────────────────────────────────────────────────────
    def _categorize_entry(self, description):
        """Categorize an entry by description. Uses learned rules first, then default keywords."""
        desc_lower = description.lower().strip()
        rules = self.data.get("category_rules", {})
        for keyword, category in rules.items():
            if keyword.lower() in desc_lower:
                return category
        for keyword, category in DEFAULT_CATEGORY_KEYWORDS.items():
            if keyword in desc_lower:
                return category
        return "Outro"

    def _show_csv_import(self):
        threading.Thread(target=self._csv_import_dialog, daemon=True).start()

    def _csv_import_dialog(self):
        dlg = tk.Tk()
        dlg.title("Importar CSV")
        dlg.configure(bg=t("BG"))
        dlg.geometry("520x600")
        dlg.resizable(False, True)
        dlg.attributes("-topmost", True)
        set_window_icon(dlg)
        dlg.after(50, lambda: style_titlebar(dlg))

        self._csv_step = 1
        self._csv_bank = None
        self._csv_entries = []
        content = tk.Frame(dlg, bg=t("BG"))
        content.pack(fill="both", expand=True, padx=24, pady=16)

        def draw_step():
            for w in content.winfo_children():
                w.destroy()
            if self._csv_step == 1:
                draw_step1()
            elif self._csv_step == 2:
                draw_step2()
            elif self._csv_step == 3:
                draw_step3()

        def draw_step1():
            tk.Label(content, text="Escolha seu banco", font=(FONT, 16, "bold"),
                     bg=t("BG"), fg=t("FG")).pack(anchor="w", pady=(0, 16))
            banks = [("Picpay", "picpay"), ("Banco do Brasil", "banco_do_brasil"),
                     ("Nubank", "nubank"), ("Bradesco", "bradesco")]
            for name, key in banks:
                btn = tk.Label(content, text=name, font=(FONT, 13),
                               bg=t("BG_CARD"), fg=t("FG"), padx=20, pady=14,
                               cursor="hand2", anchor="w",
                               highlightbackground=t("BORDER"), highlightthickness=1)
                btn.pack(fill="x", pady=(0, 6))
                btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=t("BG_HOVER")))
                btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=t("BG_CARD")))
                def select(e=None, k=key):
                    self._csv_bank = k
                    self._csv_step = 2
                    draw_step()
                btn.bind("<Button-1>", select)

        def draw_step2():
            tk.Label(content, text="Selecione o arquivo CSV", font=(FONT, 16, "bold"),
                     bg=t("BG"), fg=t("FG")).pack(anchor="w", pady=(0, 16))

            status_label = tk.Label(content, text="", font=(FONT, 10), bg=t("BG"), fg=t("DIMMED"))

            def choose_file():
                path = filedialog.askopenfilename(
                    title="Escolher CSV", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
                if not path:
                    return
                try:
                    parser = CSV_PARSERS[self._csv_bank]
                    sep = parser.get("separator", ",")
                    enc = parser.get("encoding", "utf-8")
                    with open(path, "r", encoding=enc) as f:
                        reader = csv.DictReader(f, delimiter=sep)
                        parsed = []
                        for row in reader:
                            try:
                                date_str = row[parser["date_col"]].strip()
                                desc = row[parser["desc_col"]].strip()
                                amt_str = row[parser["amount_col"]].strip()
                                amt_str = amt_str.replace("R$", "").replace(" ", "")
                                # Handle Brazilian number format: 1.234,56
                                if "," in amt_str and "." in amt_str:
                                    amt_str = amt_str.replace(".", "").replace(",", ".")
                                elif "," in amt_str:
                                    amt_str = amt_str.replace(",", ".")
                                amount = float(amt_str)
                                dt = datetime.strptime(date_str, parser["date_format"])
                                category = self._categorize_entry(desc)
                                parsed.append({
                                    "amount": amount, "description": desc,
                                    "category": category,
                                    "type": "receita" if amount >= 0 else "despesa",
                                    "timestamp": dt.isoformat(),
                                })
                            except (ValueError, KeyError):
                                continue
                        self._csv_entries = parsed
                        if parsed:
                            self._csv_step = 3
                            draw_step()
                        else:
                            status_label.configure(text="Nenhuma entrada encontrada no arquivo", fg=t("RED"))
                            status_label.pack(pady=10)
                except Exception as ex:
                    status_label.configure(text=f"Erro ao ler: {ex}", fg=t("RED"))
                    status_label.pack(pady=10)

            btn = tk.Label(content, text="Escolher arquivo CSV", font=(FONT, 13, "bold"),
                           bg=t("ACCENT"), fg="#12121a", padx=24, pady=12, cursor="hand2")
            btn.pack(fill="x", pady=10)
            btn.bind("<Button-1>", lambda e: choose_file())
            status_label.pack()

            back = tk.Label(content, text="Voltar", font=(FONT, 11),
                            bg=t("BG_HOVER"), fg=t("DIMMED"), padx=16, pady=8, cursor="hand2")
            back.pack(pady=10)
            back.bind("<Button-1>", lambda e: (setattr(self, '_csv_step', 1), draw_step()))

        def draw_step3():
            receitas = [e for e in self._csv_entries if e["amount"] >= 0]
            despesas = [e for e in self._csv_entries if e["amount"] < 0]

            tk.Label(content, text="Revisar e confirmar", font=(FONT, 16, "bold"),
                     bg=t("BG"), fg=t("FG")).pack(anchor="w")
            tk.Label(content, text=f"{len(self._csv_entries)} entradas - {len(receitas)} receitas, {len(despesas)} despesas",
                     font=(FONT, 10), bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(4, 12))

            # Scrollable list
            list_frame = tk.Frame(content, bg=t("BG"))
            list_frame.pack(fill="both", expand=True)

            style = ttk.Style()
            style.configure("CSV.TScrollbar", background=t("BG2"), troughcolor=t("BG"))

            canvas = tk.Canvas(list_frame, bg=t("BG"), highlightthickness=0)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview, style="CSV.TScrollbar")
            inner = tk.Frame(canvas, bg=t("BG"))
            cf = canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda e: canvas.itemconfig(cf, width=e.width))
            canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

            cats = self.data.get("categories", DEFAULT_CATEGORIES) + ["Outro"]

            for i, entry in enumerate(self._csv_entries[:50]):
                row_bg = t("BG_CARD") if i % 2 == 0 else t("BG2")
                row = tk.Frame(inner, bg=row_bg)
                row.pack(fill="x")

                ts = entry["timestamp"][:10]
                tk.Label(row, text=ts, font=(FONT, 9), bg=row_bg, fg=t("DIMMED"),
                         width=10).pack(side="left", padx=4, pady=3)
                tk.Label(row, text=entry["description"][:25], font=(FONT, 9),
                         bg=row_bg, fg=t("FG"), width=20, anchor="w").pack(side="left", padx=4, pady=3)

                amt = entry["amount"]
                amt_c = t("ACCENT") if amt >= 0 else t("RED")
                tk.Label(row, text=f"R${amt:,.2f}", font=(FONT, 9, "bold"),
                         bg=row_bg, fg=amt_c, width=10).pack(side="left", padx=4, pady=3)

                cat_var = tk.StringVar(value=entry["category"])
                cat_menu = ttk.Combobox(row, textvariable=cat_var, values=cats,
                                        width=10, state="readonly")
                cat_menu.pack(side="left", padx=4, pady=3)
                def on_cat_change(e=None, idx=i, var=cat_var, desc=entry["description"]):
                    self._csv_entries[idx]["category"] = var.get()
                    key = desc.strip()
                    if key:
                        self.data.setdefault("category_rules", {})[key] = var.get()
                cat_menu.bind("<<ComboboxSelected>>", on_cat_change)

            # Buttons
            btn_row = tk.Frame(content, bg=t("BG"))
            btn_row.pack(fill="x", pady=(12, 0))

            def confirm_import():
                goals = self._goals()
                goal_name = goals[0]["name"] if goals else ""
                for entry in self._csv_entries:
                    self.data["entries"].append(entry)
                    self.data["goal_assignments"][str(len(self.data["entries"]) - 1)] = goal_name
                save_data(self.data)
                self._update_icon()
                self._try_refresh()
                dlg.destroy()

            confirm = tk.Label(btn_row, text=f"Confirmar {len(self._csv_entries)} entradas",
                              font=(FONT, 12, "bold"), bg=t("ACCENT"), fg="#12121a",
                              padx=24, pady=10, cursor="hand2")
            confirm.pack(side="left", fill="x", expand=True)
            confirm.bind("<Button-1>", lambda e: confirm_import())

            back = tk.Label(btn_row, text="Voltar", font=(FONT, 11),
                            bg=t("BG_HOVER"), fg=t("DIMMED"), padx=16, pady=10, cursor="hand2")
            back.pack(side="right", padx=(8, 0))
            back.bind("<Button-1>", lambda e: (setattr(self, '_csv_step', 2), draw_step()))

        draw_step()
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.mainloop()

    def _show_config_window(self):
        threading.Thread(target=self._config_dialog, daemon=True).start()

    def _config_dialog(self):
        dlg = tk.Tk()
        dlg.title("Missionfy - Configuracoes")
        dlg.configure(bg=t("BG"))
        dlg.geometry("600x700")
        dlg.resizable(True, True)
        dlg.attributes("-topmost", True)
        set_window_icon(dlg)
        dlg.after(50, lambda: style_titlebar(dlg))

        # Scroll area
        canvas = tk.Canvas(dlg, bg=t("BG"), highlightthickness=0)
        scrollbar = ttk.Scrollbar(dlg, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=t("BG"))
        cf = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cf, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        tk.Label(frame, text="Configuracoes", font=(FONT, 16, "bold"),
                 bg=t("BG"), fg=t("FG")).pack(padx=24, pady=(16, 12), anchor="w")

        # Gerenciar Metas e Categorias
        mgmt = tk.Frame(frame, bg=t("BG"))
        mgmt.pack(fill="x", padx=24, pady=(0, 12))
        self._btn(mgmt, "Gerenciar Metas", lambda: (dlg.destroy(), self._manage_goals()), t("BLUE_DIM"), t("ACCENT2"), 11).pack(side="left", padx=(0, 6))
        self._btn(mgmt, "+ Nova Meta", lambda: (dlg.destroy(), self._add_goal()), t("GREEN_DIM"), t("ACCENT"), 11).pack(side="left", padx=(0, 6))
        self._btn(mgmt, "Categorias", lambda: (dlg.destroy(), self._manage_categories()), t("BG_HOVER"), t("YELLOW"), 11).pack(side="left")

        # Reuse existing methods
        self._draw_settings(frame)
        self._draw_history(frame)

        tk.Frame(frame, bg=t("BG"), height=20).pack()
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.mainloop()

    # ── Tab: Receitas (inline form) ───────────────────────────────────────────
    def _draw_tab_receitas(self, parent):
        PAD = 24

        # ── Título da aba ─────────────────────────────────────────────────
        header = tk.Frame(parent, bg=t("BG"))
        header.pack(fill="x", padx=PAD, pady=(12, 0))
        tk.Label(header, text="Registrar entrada", font=(FONT, 16, "bold"),
                 bg=t("BG"), fg=t("FG")).pack(anchor="w")
        tk.Label(header, text="Adicione uma receita (dinheiro que entrou) ou despesa (dinheiro que saiu)",
                 font=(FONT, 10), bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(2, 0))

        # ── Escolha: Receita ou Despesa ──────────────────────────────────
        initial_tipo = getattr(self, "_preselect_tipo", None) or "receita"
        self._preselect_tipo = None
        tipo_var = tk.StringVar(value=initial_tipo)
        choice_row = tk.Frame(parent, bg=t("BG"))
        choice_row.pack(fill="x", padx=PAD, pady=(12, 0))

        def make_tipo_card(text, subtitle, val, color, icon_char):
            card_bg = color if tipo_var.get() == val else t("BG_CARD")
            card_fg = t("BG") if tipo_var.get() == val else t("FG")
            sub_fg = t("BG") if tipo_var.get() == val else t("DIMMED")

            card = tk.Frame(choice_row, bg=card_bg, highlightbackground=t("BORDER"),
                           highlightthickness=1, cursor="hand2")
            card.pack(side="left", fill="x", expand=True, padx=3)

            inner_c = tk.Frame(card, bg=card_bg, padx=16, pady=14)
            inner_c.pack(fill="both", expand=True)

            tk.Label(inner_c, text=f"{icon_char}  {text}", font=(FONT, 14, "bold"),
                     bg=card_bg, fg=card_fg).pack(anchor="center")
            tk.Label(inner_c, text=subtitle, font=(FONT, 9),
                     bg=card_bg, fg=sub_fg).pack(anchor="center")

            def select(e=None):
                tipo_var.set(val)
                # Refresh choices
                for w in choice_row.winfo_children():
                    w.destroy()
                make_tipo_card("Receita", "Dinheiro que entrou", "receita", t("ACCENT"), "+")
                make_tipo_card("Despesa", "Dinheiro que saiu", "despesa", t("RED"), "−")

            for w in [card, inner_c] + list(inner_c.winfo_children()):
                w.bind("<Button-1>", select)

        make_tipo_card("Receita", "Dinheiro que entrou", "receita", t("ACCENT"), "+")
        make_tipo_card("Despesa", "Dinheiro que saiu", "despesa", t("RED"), "−")

        # ── Formulário ────────────────────────────────────────────────────
        card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        card.pack(fill="x", padx=PAD, pady=(10, 0))
        inner = tk.Frame(card, bg=t("BG_CARD"), padx=18, pady=14)
        inner.pack(fill="x")

        # Valor
        tk.Label(inner, text="VALOR (R$)", font=(FONT, 10),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(4, 3))
        amount_entry = tk.Entry(inner, font=(FONT, 14), bg=t("BG_INPUT"), fg=t("FG"),
                                insertbackground=t("FG"), relief="flat",
                                highlightbackground=t("BORDER"), highlightthickness=1)
        amount_entry.pack(fill="x", ipady=6)
        amount_entry.focus_set()

        # Descrição
        tk.Label(inner, text="DESCRIÇÃO", font=(FONT, 10),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(10, 3))
        desc_entry = tk.Entry(inner, font=(FONT, 12), bg=t("BG_INPUT"), fg=t("FG"),
                              insertbackground=t("FG"), relief="flat",
                              highlightbackground=t("BORDER"), highlightthickness=1)
        desc_entry.pack(fill="x", ipady=4)

        # Categoria
        cats = self.data.get("categories", DEFAULT_CATEGORIES)
        tk.Label(inner, text="CATEGORIA", font=(FONT, 10),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(10, 3))
        cat_frame = tk.Frame(inner, bg=t("BG_CARD"))
        cat_frame.pack(fill="x")
        cat_frame.columnconfigure(0, weight=1)
        cat_frame.columnconfigure(1, weight=1)
        cat_frame.columnconfigure(2, weight=1)
        selected_cat = tk.StringVar(value=cats[0] if cats else "Outro")

        for idx, cat in enumerate(cats):
            def make_cat_btn(c, i):
                is_sel = c == selected_cat.get()
                btn = tk.Label(cat_frame, text=c, font=(FONT, 10),
                               padx=10, pady=4, cursor="hand2",
                               bg=t("ACCENT2") if is_sel else t("BG_HOVER"),
                               fg=t("BG") if is_sel else t("FG"))
                def select(e=None):
                    selected_cat.set(c)
                    for w in cat_frame.winfo_children():
                        w.configure(bg=t("BG_HOVER"), fg=t("FG"))
                    btn.configure(bg=t("ACCENT2"), fg=t("BG"))
                btn.bind("<Button-1>", select)
                row, col = divmod(i, 3)
                btn.grid(row=row, column=col, padx=(0, 4), pady=2, sticky="ew")
            make_cat_btn(cat, idx)

        # Meta (se mais de uma)
        goals = self._goals()
        selected_goal = tk.StringVar(value=goals[0]["name"] if goals else "")
        if len(goals) > 1:
            tk.Label(inner, text="MISSÃO", font=(FONT, 10),
                     bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(10, 3))
            goal_frame = tk.Frame(inner, bg=t("BG_CARD"))
            goal_frame.pack(fill="x")
            for g in goals:
                def make_g_btn(gn):
                    is_sel = gn == selected_goal.get()
                    btn = tk.Label(goal_frame, text=gn, font=(FONT, 10),
                                   padx=10, pady=4, cursor="hand2",
                                   bg=t("ACCENT2") if is_sel else t("BG_HOVER"),
                                   fg=t("BG") if is_sel else t("FG"))
                    def select(e=None):
                        selected_goal.set(gn)
                        for w in goal_frame.winfo_children():
                            w.configure(bg=t("BG_HOVER"), fg=t("FG"))
                        btn.configure(bg=t("ACCENT2"), fg=t("BG"))
                    btn.bind("<Button-1>", select)
                    btn.pack(side="left", padx=(0, 4), pady=2)
                make_g_btn(g["name"])

        # Botão salvar
        def save():
            amt_str = amount_entry.get().strip()
            if not amt_str:
                return
            try:
                amount = float(amt_str.replace("R$", "").replace("$", "").replace(",", "."))
                if tipo_var.get() == "despesa":
                    amount = -abs(amount)
            except ValueError:
                return

            entry = {
                "amount": amount,
                "description": desc_entry.get().strip() or "Sem descrição",
                "category": selected_cat.get(),
                "type": tipo_var.get(),
                "timestamp": datetime.now().isoformat(),
            }
            self.data["entries"].append(entry)
            self.data["goal_assignments"][str(len(self.data["entries"]) - 1)] = selected_goal.get()
            save_data(self.data)
            self._update_icon()

            # Notification
            try:
                if self.icon:
                    goal = self._main_goal()
                    total = self._main_total()
                    pp = int(pct(total, goal) * 100)
                    sign = "+" if amount >= 0 else ""
                    self.icon.notify(f"{sign}R${amount:,.2f} registrado! Progresso: {pp}%", "Missionfy")
            except Exception:
                pass

            # Clear form
            amount_entry.delete(0, tk.END)
            desc_entry.delete(0, tk.END)
            amount_entry.focus_set()

        save_row = tk.Frame(inner, bg=t("BG_CARD"))
        save_row.pack(fill="x", pady=(14, 0))
        save_btn = tk.Label(save_row, text="Salvar", font=(FONT, 12, "bold"),
                            bg=t("ACCENT"), fg=t("BG"), pady=10, cursor="hand2")
        save_btn.bind("<Button-1>", lambda e: save())
        save_btn.bind("<Enter>", lambda e: save_btn.configure(bg=self._lighten(t("ACCENT"))))
        save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=t("ACCENT")))
        save_btn.pack(fill="x")

        # Enter to save
        def on_enter(e):
            save()
        amount_entry.bind("<Return>", lambda e: desc_entry.focus_set())
        desc_entry.bind("<Return>", on_enter)

        # ── Entradas recentes ─────────────────────────────────────────────
        entries = self.data["entries"]
        if entries:
            tk.Label(parent, text="ENTRADAS RECENTES", font=(FONT, 10, "bold"),
                     bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", padx=PAD, pady=(14, 6))

            asgn = self.data.get("goal_assignments", {})
            default_g = goals[0]["name"] if goals else "—"

            for i in range(len(entries) - 1, max(len(entries) - 10, -1), -1):
                e = entries[i]
                rbg = t("BG_CARD") if (len(entries) - 1 - i) % 2 == 0 else t("BG2")
                row = tk.Frame(parent, bg=rbg)
                row.pack(fill="x", padx=PAD)

                ts = e["timestamp"][:16].replace("T", "  ")
                tk.Label(row, text=ts, font=(FONT, 10), bg=rbg, fg=t("DIMMED"),
                         width=14).pack(side="left", padx=8, pady=4)
                tk.Label(row, text=e.get("description", "—")[:20], font=(FONT, 10), bg=rbg, fg=t("FG")).pack(side="left", padx=4, pady=4)

                amt = e["amount"]
                sign = "+" if amt >= 0 else ""
                amt_c = t("ACCENT") if amt >= 0 else t("RED")
                tk.Label(row, text=f"{sign}R${amt:,.2f}", font=(FONT, 11, "bold"),
                         bg=rbg, fg=amt_c).pack(side="right", padx=8, pady=4)
                tk.Label(row, text=e.get("category", ""), font=(FONT, 9),
                         bg=rbg, fg=t("DIMMED")).pack(side="right", padx=4, pady=4)

    def _btn(self, parent, text, cmd, bg_c=None, fg_c=None, size=9):
        bg_c = bg_c or t("BG_HOVER")
        fg_c = fg_c or t("FG")
        lbl = tk.Label(parent, text=text, font=(FONT, size), bg=bg_c, fg=fg_c,
                       padx=10, pady=4, cursor="hand2")
        lbl.bind("<Button-1>", lambda e: cmd())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=self._lighten(bg_c)))
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=bg_c))
        return lbl

    @staticmethod
    def _lighten(hx, amt=20):
        hx = hx.lstrip("#")
        return "#{:02x}{:02x}{:02x}".format(
            min(255, int(hx[0:2], 16) + amt), min(255, int(hx[2:4], 16) + amt), min(255, int(hx[4:6], 16) + amt))

    # ── Goal Card ─────────────────────────────────────────────────────────────
    # ── Gamification card ───────────────────────────────────────────────────
    def _draw_gamification(self, parent):
        goal = self._main_goal()
        gm = calc_gamification(self.data, goal)
        PAD = 24

        card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=gm["level_color"], highlightthickness=2)
        card.pack(fill="x", padx=PAD, pady=(8, 0))
        inner = tk.Frame(card, bg=t("BG_CARD"), padx=16, pady=10)
        inner.pack(fill="x")

        # Row 1: Level + XP + Streak
        row1 = tk.Frame(inner, bg=t("BG_CARD"))
        row1.pack(fill="x")

        # Level badge
        tk.Label(row1, text=f"⚡ {gm['level']}", font=(FONT, 13, "bold"),
                 bg=t("BG_CARD"), fg=gm["level_color"]).pack(side="left")

        # Streak
        if gm["streak"] > 0:
            tk.Label(row1, text=f"🔥 {gm['streak']} dias", font=(FONT, 11),
                     bg=t("BG_CARD"), fg=t("YELLOW")).pack(side="left", padx=(12, 0))

        # XP
        tk.Label(row1, text=f"{gm['xp']} XP", font=(FONT, 11, "bold"),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(side="right")

        # XP progress bar
        xp_bar = tk.Frame(inner, bg=t("BAR_BG"), height=6)
        xp_bar.pack(fill="x", pady=(6, 4))
        xp_bar.pack_propagate(False)
        if gm["level_progress"] > 0:
            tk.Frame(xp_bar, bg=gm["level_color"], height=6).place(
                relx=0, rely=0, relwidth=min(gm["level_progress"], 1.0), relheight=1.0)

        tk.Label(inner, text=f"Próximo nível: {gm['next_xp']} XP", font=(FONT, 9),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w")

        # Medals row
        earned = gm["earned"]
        if earned:
            medals_frame = tk.Frame(inner, bg=t("BG_CARD"))
            medals_frame.pack(fill="x", pady=(8, 0))

            for medal_id, medal_name, medal_desc, medal_icon in MEDALS:
                is_earned = medal_id in earned
                bg_c = t("GREEN_DIM") if is_earned else t("BG_HOVER")
                fg_c = t("ACCENT") if is_earned else t("DIMMED")
                opacity_fg = t("FG") if is_earned else t("DIMMED")

                m = tk.Frame(medals_frame, bg=bg_c, padx=4, pady=2)
                m.pack(side="left", padx=(0, 4), pady=2)
                tk.Label(m, text=f"{medal_icon} {medal_name}", font=(FONT, 8),
                         bg=bg_c, fg=opacity_fg).pack()

    def _draw_goal_card(self, parent, goal):
        ents = entries_for_goal(self.data, goal["name"])
        revenue = sum(e["amount"] for e in ents if e["amount"] > 0)
        expenses = sum(e["amount"] for e in ents if e["amount"] < 0)
        total = revenue
        today = today_sum([e for e in ents if e["amount"] > 0])
        remaining = max(goal["amount"] - total, 0)
        pace = current_pace(total, goal)
        dl = days_left(goal)
        elapsed = days_elapsed(goal)
        progress = pct(total, goal)
        projected = pace * dl
        daily_needed = remaining / dl if dl > 0 else 0
        color = t("ACCENT") if progress >= 0.75 else (t("YELLOW") if progress >= 0.4 else t("RED"))

        card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        card.pack(fill="x", padx=24, pady=(4, 0))
        inner = tk.Frame(card, bg=t("BG_CARD"), padx=16, pady=10)
        inner.pack(fill="x")

        # Row 1: Nome + porcentagem grande
        r1 = tk.Frame(inner, bg=t("BG_CARD"))
        r1.pack(fill="x")

        left_col = tk.Frame(r1, bg=t("BG_CARD"))
        left_col.pack(side="left")
        tk.Label(left_col, text=goal["name"], font=(FONT, 14, "bold"),
                 bg=t("BG_CARD"), fg=t("FG")).pack(anchor="w")
        tk.Label(left_col, text=f"{goal['start_date'].strftime('%d/%m/%Y')}  a  {goal['end_date'].strftime('%d/%m/%Y')}",
                 font=(FONT, 10), bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w")

        right_col = tk.Frame(r1, bg=t("BG_CARD"))
        right_col.pack(side="right")
        tk.Label(right_col, text=f"{int(progress * 100)}%", font=(FONT, 24, "bold"),
                 bg=t("BG_CARD"), fg=color).pack(anchor="e")

        # Progress bar
        bar_outer = tk.Frame(inner, bg=t("BAR_BG"), height=10)
        bar_outer.pack(fill="x", pady=(12, 10))
        bar_outer.pack_propagate(False)
        if progress > 0:
            bar_fill = tk.Frame(bar_outer, bg=color, height=10)
            bar_fill.place(relx=0, rely=0, relwidth=0, relheight=1.0)
            bar_outer.after(50, lambda bf=bar_fill, p=progress: bf.place(relwidth=min(p, 1.0)))

        # Big numbers row
        big_row = tk.Frame(inner, bg=t("BG_CARD"))
        big_row.pack(fill="x", pady=(2, 8))
        tk.Label(big_row, text=f"R${revenue:,.2f}", font=(FONT, 16, "bold"),
                 bg=t("BG_CARD"), fg=t("ACCENT")).pack(side="left")
        tk.Label(big_row, text=f"de R${goal['amount']:,}", font=(FONT, 12),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(side="left", padx=(8, 0), pady=(4, 0))
        if remaining > 0:
            tk.Label(big_row, text=f"faltam R${remaining:,.2f}", font=(FONT, 12),
                     bg=t("BG_CARD"), fg=t("YELLOW")).pack(side="right")

        # Stats grid
        tk.Frame(inner, bg=t("BORDER"), height=1).pack(fill="x", pady=(0, 8))
        stats = tk.Frame(inner, bg=t("BG_CARD"))
        stats.pack(fill="x")
        data_rows = [
            ("Hoje", f"R${today:,.2f}", t("FG")),
            ("Despesas", f"R${abs(expenses):,.2f}", t("RED") if expenses < 0 else t("DIMMED")),
            ("Ritmo", f"R${pace:,.2f}/dia", t("FG")),
            ("Precisa/dia", f"R${daily_needed:,.2f}", t("ACCENT2")),
            ("Dias restantes", str(dl), t("RED") if dl < 30 else t("FG")),
            ("Projetado", f"R${projected:,.0f}", t("ACCENT") if projected >= goal["amount"] else t("RED")),
        ]
        for i, (lbl, val, vc) in enumerate(data_rows):
            row, col = divmod(i, 3)
            f = tk.Frame(stats, bg=t("BG_CARD"))
            f.grid(row=row, column=col, padx=8, pady=4, sticky="w")
            stats.columnconfigure(col, weight=1)
            tk.Label(f, text=lbl.upper(), font=(FONT, 9), bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w")
            tk.Label(f, text=val, font=(FONT, 13, "bold"), bg=t("BG_CARD"), fg=vc).pack(anchor="w")

    # ── Balance + Summary combined ──────────────────────────────────────────
    def _draw_balance_and_summary(self, parent):
        entries = self.data["entries"]
        if not entries:
            return

        revenue = sum(e["amount"] for e in entries if e["amount"] > 0)
        expenses = sum(e["amount"] for e in entries if e["amount"] < 0)
        balance = revenue + expenses
        today_d = date.today()

        week_start = today_d - timedelta(days=today_d.weekday())
        week_rev = sum(e["amount"] for e in entries if e["amount"] > 0 and e["timestamp"][:10] >= week_start.isoformat())
        month_start = today_d.replace(day=1).isoformat()
        month_rev = sum(e["amount"] for e in entries if e["amount"] > 0 and e["timestamp"][:10] >= month_start)
        month_exp = sum(e["amount"] for e in entries if e["amount"] < 0 and e["timestamp"][:10] >= month_start)

        sec_title = tk.Frame(parent, bg=t("BG"))
        sec_title.pack(fill="x", padx=24, pady=(16, 6))
        tk.Label(sec_title, text="RESUMO FINANCEIRO", font=(FONT, 10, "bold"),
                 bg=t("BG"), fg=t("DIMMED")).pack(side="left")

        card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        card.pack(fill="x", padx=24, pady=(0, 0))
        inner = tk.Frame(card, bg=t("BG_CARD"), padx=18, pady=14)
        inner.pack(fill="x")

        # Saldo grande
        bal_color = t("ACCENT") if balance >= 0 else t("RED")
        bal_row = tk.Frame(inner, bg=t("BG_CARD"))
        bal_row.pack(fill="x", pady=(0, 10))
        tk.Label(bal_row, text="SALDO LÍQUIDO", font=(FONT, 10), bg=t("BG_CARD"), fg=t("DIMMED")).pack(side="left")
        tk.Label(bal_row, text=f"R${balance:,.2f}", font=(FONT, 20, "bold"),
                 bg=t("BG_CARD"), fg=bal_color).pack(side="right")

        tk.Frame(inner, bg=t("BORDER"), height=1).pack(fill="x", pady=(0, 10))

        # Stats row
        cols_data = [
            ("Receitas", f"R${revenue:,.2f}", t("ACCENT")),
            ("Despesas", f"R${abs(expenses):,.2f}", t("RED")),
            ("Semana", f"R${week_rev:,.2f}", t("FG")),
            ("Mês", f"R${month_rev:,.2f}", t("ACCENT")),
        ]
        for lbl, val, vc in cols_data:
            f = tk.Frame(inner, bg=t("BG_CARD"))
            f.pack(side="left", expand=True, fill="x")
            tk.Label(f, text=lbl.upper(), font=(FONT, 9), bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w")
            tk.Label(f, text=val, font=(FONT, 12, "bold"), bg=t("BG_CARD"), fg=vc).pack(anchor="w")

    # ── Charts row (progress + category side by side) ──────────────────────
    def _draw_charts_row(self, parent):
        entries = [e for e in self.data["entries"] if e["amount"] > 0]
        if not entries:
            return

        row = tk.Frame(parent, bg=t("BG"))
        row.pack(fill="x", padx=24, pady=(4, 0))

        # ── Progress chart (left) ─────────────────────────────────────────
        left = tk.Frame(row, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))

        tk.Label(left, text="PROGRESSO", font=(FONT, 10, "bold"), bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", padx=10, pady=(8, 0))

        cw, ch = 340, 160
        c = tk.Canvas(left, width=cw, height=ch, bg=t("BG_CARD"), highlightthickness=0)
        c.pack(padx=8, pady=(0, 8))

        daily = defaultdict(float)
        for e in entries:
            daily[e["timestamp"][:10]] += e["amount"]
        sorted_d = sorted(daily.keys())

        # Add origin point if only 1 day
        cum, run = [], 0
        if len(sorted_d) == 1:
            cum.append((sorted_d[0], 0))  # start from zero
        for d in sorted_d:
            run += daily[d]
            cum.append((d, run))

        ga = self._main_goal()["amount"]
        max_y = max(ga, cum[-1][1])
        mv = max_y * 1.15 if max_y > 0 else 1
        pl, pr, pt, pb = 50, 12, 12, 24
        pw, ph = cw - pl - pr, ch - pt - pb

        # Grid lines
        for frac in [0.25, 0.5, 0.75]:
            gy = pt + ph * (1 - frac)
            c.create_line(pl, gy, cw - pr, gy, fill=t("GRID"), dash=(2, 4))
            c.create_text(pl - 6, gy, text=f"R${mv * frac:,.0f}", anchor="e", fill=t("DIMMED"), font=(FONT, 7))

        # Goal line
        gy = pt + ph * (1 - ga / mv)
        c.create_line(pl, gy, cw - pr, gy, fill=t("RED"), dash=(4, 3))
        c.create_text(pl - 6, gy, text="MISSÃO", anchor="e", fill=t("RED"), font=(FONT, 7, "bold"))

        # Points
        pts = []
        n = max(len(cum) - 1, 1)
        for i, (d, v) in enumerate(cum):
            x = pl + (i / n) * pw
            y = pt + ph * (1 - v / mv)
            pts.append((x, y))

        # Filled area
        if len(pts) >= 2:
            poly = [(pts[0][0], pt + ph)] + pts + [(pts[-1][0], pt + ph)]
            c.create_polygon(poly, fill=t("CHART_FILL"), outline="")
            for i in range(len(pts) - 1):
                c.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], fill=t("ACCENT"), width=2)
        for x, y in pts:
            c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=t("ACCENT"), outline=t("BG_CARD"))

        # X axis
        c.create_text(pl, ch - 5, text=cum[0][0][5:], anchor="w", fill=t("DIMMED"), font=(FONT, 8))
        if len(cum) > 1:
            c.create_text(cw - pr, ch - 5, text=cum[-1][0][5:], anchor="e", fill=t("DIMMED"), font=(FONT, 8))

        # ── Category pie (right) ──────────────────────────────────────────
        by_cat = defaultdict(float)
        for e in entries:
            by_cat[e.get("category", "Outro")] += e["amount"]
        if not by_cat:
            return

        right = tk.Frame(row, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        right.pack(side="left", fill="both", expand=True, padx=(4, 0))

        tk.Label(right, text="CATEGORIAS", font=(FONT, 12, "bold"), bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", padx=10, pady=(6, 0))

        pie_inner = tk.Frame(right, bg=t("BG_CARD"))
        pie_inner.pack(fill="x", padx=8, pady=(0, 6))

        pie_size = 100
        pc = tk.Canvas(pie_inner, width=pie_size, height=pie_size, bg=t("BG_CARD"), highlightthickness=0)
        pc.pack(side="left", padx=(0, 8))

        colors = ["#3fb950", "#58a6ff", "#d29922", "#f85149", "#a371f7", "#79c0ff", "#d2a8ff", "#f0883e"]
        total_cat = sum(by_cat.values())
        start = 0
        sorted_cats = sorted(by_cat.items(), key=lambda x: -x[1])

        for i, (cat, val) in enumerate(sorted_cats):
            ext = (val / total_cat) * 360
            clr = colors[i % len(colors)]
            pc.create_arc(5, 5, pie_size - 5, pie_size - 5, start=start, extent=ext,
                          fill=clr, outline=t("BG_CARD"), width=1)
            start += ext

        legend = tk.Frame(pie_inner, bg=t("BG_CARD"))
        legend.pack(side="left", fill="both", expand=True)
        for i, (cat, val) in enumerate(sorted_cats[:5]):
            clr = colors[i % len(colors)]
            lr = tk.Frame(legend, bg=t("BG_CARD"))
            lr.pack(fill="x", pady=1)
            dot = tk.Canvas(lr, width=8, height=8, bg=t("BG_CARD"), highlightthickness=0)
            dot.create_oval(1, 1, 7, 7, fill=clr, outline="")
            dot.pack(side="left", padx=(0, 4))
            pctv = int((val / total_cat) * 100)
            tk.Label(lr, text=f"{cat} {pctv}%", font=(FONT, 12), bg=t("BG_CARD"), fg=t("FG")).pack(side="left")

    # ── History ───────────────────────────────────────────────────────────────
    def _draw_history(self, parent):
        entries = self.data["entries"]
        if not entries:
            return

        sec = tk.Frame(parent, bg=t("BG"))
        sec.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(sec, text="Histórico", font=("Segoe UI Semibold", 11), bg=t("BG"), fg=t("FG")).pack(side="left")
        tk.Label(sec, text=f"{len(entries)} registros", font=(FONT, 12), bg=t("BG"), fg=t("DIMMED")).pack(side="right")

        # Filter by category
        filter_frame = tk.Frame(parent, bg=t("BG"))
        filter_frame.pack(fill="x", padx=20, pady=(3, 0))

        self._current_filter = getattr(self, "_current_filter", "Todos")
        cats = ["Todos"] + self.data.get("categories", DEFAULT_CATEGORIES)

        for cat in cats:
            is_active = cat == self._current_filter
            bg_c = t("ACCENT2") if is_active else t("BG_HOVER")
            fg_c = t("BG") if is_active else t("DIMMED")
            btn = tk.Label(filter_frame, text=cat, font=(FONT, 12), bg=bg_c, fg=fg_c,
                           padx=8, pady=2, cursor="hand2")
            btn.bind("<Button-1>", lambda e, c=cat: self._set_filter(c))
            btn.pack(side="left", padx=2)

        tbl = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        tbl.pack(fill="x", padx=20, pady=(4, 0))

        hdr = tk.Frame(tbl, bg=t("BG2"))
        hdr.pack(fill="x")
        for txt, w in [("DATA", 13), ("DESCRIÇÃO", 18), ("CATEGORIA", 10), ("MISSÃO", 11), ("VALOR", 10), ("", 10)]:
            tk.Label(hdr, text=txt, font=(FONT, 12, "bold"), bg=t("BG2"), fg=t("DIMMED"),
                     width=w, anchor="w").pack(side="left", padx=3, pady=5)

        asgn = self.data.get("goal_assignments", {})
        goals = self._goals()
        default_g = goals[0]["name"] if goals else "—"

        shown = 0
        for i in range(len(entries) - 1, -1, -1):
            e = entries[i]
            cat = e.get("category", "Outro")
            if self._current_filter != "Todos" and cat != self._current_filter:
                continue
            if shown >= 25:
                break
            shown += 1

            assigned = asgn.get(str(i), default_g)
            rbg = t("BG_CARD") if shown % 2 == 1 else t("BG2")

            row = tk.Frame(tbl, bg=rbg)
            row.pack(fill="x")

            ts = e["timestamp"][:16].replace("T", "  ")
            tk.Label(row, text=ts, font=(FONT, 12), bg=rbg, fg=t("FG2"), width=13, anchor="w").pack(side="left", padx=3, pady=3)
            tk.Label(row, text=e.get("description", "—")[:18], font=(FONT, 12), bg=rbg, fg=t("FG"), width=18, anchor="w").pack(side="left", padx=3, pady=3)
            tk.Label(row, text=cat[:10], font=(FONT, 12), bg=rbg, fg=t("DIMMED"), width=10, anchor="w").pack(side="left", padx=3, pady=3)
            tk.Label(row, text=assigned[:11], font=(FONT, 12), bg=rbg, fg=t("DIMMED"), width=11, anchor="w").pack(side="left", padx=3, pady=3)

            amt = e["amount"]
            amt_color = t("ACCENT") if amt >= 0 else t("RED")
            sign = "+" if amt >= 0 else ""
            tk.Label(row, text=f"{sign}R${amt:,.2f}", font=(FONT, 12, "bold"), bg=rbg, fg=amt_color, width=10, anchor="e").pack(side="left", padx=3, pady=3)

            bf = tk.Frame(row, bg=rbg)
            bf.pack(side="left", padx=3)
            eb = tk.Label(bf, text="✏", font=(FONT, 12), bg=t("BLUE_DIM"), fg=t("ACCENT2"), padx=4, pady=0, cursor="hand2")
            eb.bind("<Button-1>", lambda e, idx=i: self._edit_entry(idx))
            eb.pack(side="left", padx=(0, 2))
            db = tk.Label(bf, text="X", font=(FONT, 12, "bold"), bg=t("RED_DIM"), fg=t("RED"), padx=4, pady=0, cursor="hand2")
            db.bind("<Button-1>", lambda e, idx=i: self._delete_entry(idx))
            db.pack(side="left")

    def _set_filter(self, cat):
        self._current_filter = cat
        self._refresh_dashboard(keep_scroll=True)

    # ── Daily Target ──────────────────────────────────────────────────────────
    def _draw_daily_target(self, parent):
        goal = self._main_goal()
        total = self._main_total()
        remaining = max(goal["amount"] - total, 0)
        dl = days_left(goal)
        if dl <= 0 or remaining <= 0:
            return

        daily = remaining / dl
        progress = pct(total, goal)
        today_rev = today_sum([e for e in entries_for_goal(self.data, goal["name"]) if e["amount"] > 0])
        on_track = today_rev >= daily

        card = tk.Frame(parent, bg=t("BLUE_DIM"), highlightbackground=t("ACCENT2"), highlightthickness=1)
        card.pack(fill="x", padx=24, pady=(8, 0))
        inner = tk.Frame(card, bg=t("BLUE_DIM"), padx=16, pady=8)
        inner.pack(fill="x")

        row = tk.Frame(inner, bg=t("BLUE_DIM"))
        row.pack(fill="x")
        tk.Label(row, text="🎯 MISSÃO DIÁRIA", font=(FONT, 10),
                 bg=t("BLUE_DIM"), fg=t("DIMMED")).pack(side="left")
        tk.Label(row, text=f"R${daily:,.2f}/dia", font=(FONT, 14, "bold"),
                 bg=t("BLUE_DIM"), fg=t("ACCENT2")).pack(side="left", padx=(10, 0))

        if on_track:
            tk.Label(row, text="✓ No ritmo!", font=(FONT, 11, "bold"),
                     bg=t("BLUE_DIM"), fg=t("ACCENT")).pack(side="right")
        else:
            falta = max(daily - today_rev, 0)
            tk.Label(row, text=f"Faltam R${falta:,.2f} hoje", font=(FONT, 11, "bold"),
                     bg=t("BLUE_DIM"), fg=t("YELLOW")).pack(side="right")

    # ── Edit / Delete ─────────────────────────────────────────────────────────
    def _edit_entry(self, idx):
        win = self.dashboard_window
        if not win:
            return
        e = self.data["entries"][idx]

        new_amount = simpledialog.askstring("Editar", f"Valor atual: R${e['amount']:,.2f}\nNovo valor:",
                                            parent=win, initialvalue=str(e["amount"]))
        if new_amount is None:
            return
        try:
            self.data["entries"][idx]["amount"] = float(new_amount.strip().replace("R$", "").replace("$", "").replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Valor inválido.", parent=win)
            return

        new_desc = simpledialog.askstring("Editar", "Descrição:", parent=win, initialvalue=e.get("description", ""))
        if new_desc is not None:
            self.data["entries"][idx]["description"] = new_desc.strip() or "Sem descrição"

        save_data(self.data)
        self._update_icon()
        self._refresh_dashboard()

    def _delete_entry(self, idx):
        win = self.dashboard_window
        if not win:
            return
        e = self.data["entries"][idx]
        if not messagebox.askyesno("Excluir", f"Excluir R${e['amount']:,.2f} — {e.get('description', '—')}?", parent=win):
            return
        self.data["entries"].pop(idx)
        old = self.data.get("goal_assignments", {})
        new = {}
        for k, v in old.items():
            ki = int(k)
            if ki < idx:
                new[str(ki)] = v
            elif ki > idx:
                new[str(ki - 1)] = v
        self.data["goal_assignments"] = new
        save_data(self.data)
        self._update_icon()
        self._refresh_dashboard()

    # ── Manage Goals ──────────────────────────────────────────────────────────
    def _manage_goals(self):
        threading.Thread(target=self._manage_goals_dialog, daemon=True).start()

    def _manage_goals_dialog(self):
        goals = self.data.get("goals", [])
        if not goals:
            return

        dlg = tk.Tk()
        dlg.title("Gerenciar Missões")
        dlg.configure(bg=t("BG"))
        dlg.geometry("420x400")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        set_window_icon(dlg)
        dlg.after(50, lambda: style_titlebar(dlg))

        tk.Label(dlg, text="Gerenciar Missões", font=(FONT, 14, "bold"),
                 bg=t("BG"), fg=t("FG")).pack(pady=(18, 5))
        tk.Label(dlg, text="Clique numa missão para editar", font=(FONT, 12),
                 bg=t("BG"), fg=t("DIMMED")).pack(pady=(0, 10))

        list_f = tk.Frame(dlg, bg=t("BG"))
        list_f.pack(fill="both", expand=True, padx=25)

        for i, g in enumerate(goals):
            gt = total_sum(entries_for_goal(self.data, g["name"]))
            gobj = get_goals(self.data)[i] if i < len(get_goals(self.data)) else None
            gp = pct(gt, gobj) if gobj else 0
            gc = t("ACCENT") if gp >= 0.75 else (t("YELLOW") if gp >= 0.4 else t("RED"))

            row_bg = t("BG_CARD") if i % 2 == 0 else t("BG2")
            row = tk.Frame(list_f, bg=row_bg, cursor="hand2")
            row.pack(fill="x", pady=1)

            info = tk.Frame(row, bg=row_bg)
            info.pack(side="left", fill="x", expand=True, padx=12, pady=8)
            tk.Label(info, text=g["name"], font=(FONT, 12, "bold"),
                     bg=row_bg, fg=t("FG")).pack(anchor="w")
            tk.Label(info, text=f"R${gt:,.2f} / R${g['amount']:,},  {g['start_date']}  a  {g['end_date']}",
                     font=(FONT, 12), bg=row_bg, fg=t("DIMMED")).pack(anchor="w")

            pct_lbl = tk.Label(row, text=f"{int(gp * 100)}%", font=(FONT, 12, "bold"),
                               bg=row_bg, fg=gc, padx=12)
            pct_lbl.pack(side="right")

            for w in (row, info, pct_lbl):
                w.bind("<Button-1>", lambda e, idx=i, goal=g: (dlg.destroy(), self._edit_goal(idx, goal)))
                w.bind("<Enter>", lambda e, r=row, bg=row_bg: [c.configure(bg=t("BG_HOVER")) for c in [r] + list(r.winfo_children()) + [w for f in r.winfo_children() for w in f.winfo_children() if isinstance(f, tk.Frame)]])
                w.bind("<Leave>", lambda e, r=row, bg=row_bg: [c.configure(bg=bg) for c in [r] + list(r.winfo_children()) + [w for f in r.winfo_children() for w in f.winfo_children() if isinstance(f, tk.Frame)]])

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.mainloop()

    def _goal_form(self, title, values, on_save, on_delete=None):
        """Shared form for editing and creating goals."""
        dlg = tk.Tk()
        dlg.title(title)
        dlg.configure(bg=t("BG"))
        dlg.geometry("480x520")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        set_window_icon(dlg)
        dlg.after(50, lambda: style_titlebar(dlg))

        tk.Label(dlg, text=title, font=(FONT, 14, "bold"),
                 bg=t("BG"), fg=t("FG")).pack(pady=(18, 12))

        form = tk.Frame(dlg, bg=t("BG"))
        form.pack(padx=30, fill="x")

        fields = {}

        # Nome
        tk.Label(form, text="NOME DA MISSÃO", font=(FONT, 10),
                 bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(0, 3))
        fields["name"] = tk.Entry(form, font=(FONT, 12), bg=t("BG_INPUT"), fg=t("FG"),
                                  insertbackground=t("FG"), relief="flat",
                                  highlightbackground=t("BORDER"), highlightthickness=1)
        fields["name"].insert(0, values.get("name", ""))
        fields["name"].pack(fill="x", ipady=5)

        # Valor
        tk.Label(form, text="VALOR (R$)", font=(FONT, 10),
                 bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(10, 3))
        fields["amount"] = tk.Entry(form, font=(FONT, 12), bg=t("BG_INPUT"), fg=t("FG"),
                                    insertbackground=t("FG"), relief="flat",
                                    highlightbackground=t("BORDER"), highlightthickness=1)
        fields["amount"].insert(0, values.get("amount", ""))
        fields["amount"].pack(fill="x", ipady=5)

        # Data início
        tk.Label(form, text="DATA INICIO (dd/mm/aaaa)", font=(FONT, 10),
                 bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(10, 3))
        fields["start_date"] = tk.Entry(form, font=(FONT, 12), bg=t("BG_INPUT"), fg=t("FG"),
                                        insertbackground=t("FG"), relief="flat",
                                        highlightbackground=t("BORDER"), highlightthickness=1)
        sd_val = values.get("start_date", date.today().isoformat())
        try:
            sd_parsed = date.fromisoformat(sd_val)
            sd_display = sd_parsed.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            sd_display = sd_val
        fields["start_date"].insert(0, sd_display)
        fields["start_date"].pack(fill="x", ipady=5)

        # Data limite com atalhos
        tk.Label(form, text="DATA LIMITE (dd/mm/aaaa)", font=(FONT, 10),
                 bg=t("BG"), fg=t("DIMMED")).pack(anchor="w", pady=(10, 3))

        shortcut_row = tk.Frame(form, bg=t("BG"))
        shortcut_row.pack(fill="x", pady=(0, 4))
        for label, dias in [("3 meses", 90), ("6 meses", 180), ("1 ano", 365), ("2 anos", 730)]:
            def make_shortcut(d):
                btn = tk.Label(shortcut_row, text=label, font=(FONT, 9), bg=t("BG_HOVER"), fg=t("DIMMED"),
                               padx=8, pady=3, cursor="hand2")
                def click(e=None):
                    end = date.today() + timedelta(days=d)
                    fields["end_date"].delete(0, tk.END)
                    fields["end_date"].insert(0, end.strftime("%d/%m/%Y"))
                    for w in shortcut_row.winfo_children():
                        w.configure(bg=t("BG_HOVER"), fg=t("DIMMED"))
                    btn.configure(bg=t("ACCENT"), fg=t("BG"))
                btn.bind("<Button-1>", click)
                btn.pack(side="left", padx=(0, 4))
            make_shortcut(dias)

        fields["end_date"] = tk.Entry(form, font=(FONT, 12), bg=t("BG_INPUT"), fg=t("FG"),
                                      insertbackground=t("FG"), relief="flat",
                                      highlightbackground=t("BORDER"), highlightthickness=1)
        ed_val = values.get("end_date", (date.today() + timedelta(days=365)).isoformat())
        try:
            ed_parsed = date.fromisoformat(ed_val)
            ed_display = ed_parsed.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            ed_display = ed_val
        fields["end_date"].insert(0, ed_display)
        fields["end_date"].pack(fill="x", ipady=5)

        fields["name"].focus_set()

        def do_save():
            try:
                nm = fields["name"].get().strip()
                if not nm:
                    raise ValueError("Nome e obrigatorio")
                amt = float(fields["amount"].get().strip().replace(",", "."))
                sd_raw = fields["start_date"].get().strip()
                ed_raw = fields["end_date"].get().strip()
                # Aceitar dd/mm/aaaa ou aaaa-mm-dd
                try:
                    sd = datetime.strptime(sd_raw, "%d/%m/%Y").date().isoformat()
                except ValueError:
                    sd = sd_raw
                    date.fromisoformat(sd)
                try:
                    ed = datetime.strptime(ed_raw, "%d/%m/%Y").date().isoformat()
                except ValueError:
                    ed = ed_raw
                    date.fromisoformat(ed)
            except (ValueError, TypeError) as ex:
                messagebox.showerror("Erro", f"Verifique os campos.\n{ex}", parent=dlg)
                return
            on_save(nm, amt, sd, ed)
            dlg.destroy()
            self._update_icon()
            self._refresh_dashboard()

        btn_row = tk.Frame(dlg, bg=t("BG"))
        btn_row.pack(pady=(20, 0))

        save_btn = tk.Label(btn_row, text="Salvar", font=(FONT, 12),
                            bg=t("ACCENT"), fg=t("BG"), padx=24, pady=7, cursor="hand2")
        save_btn.bind("<Button-1>", lambda e: do_save())
        save_btn.bind("<Enter>", lambda e: save_btn.configure(bg=self._lighten(t("ACCENT"))))
        save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=t("ACCENT")))
        save_btn.pack(side="left", padx=5)

        cancel_btn = tk.Label(btn_row, text="Cancelar", font=(FONT, 12),
                              bg=t("BG_HOVER"), fg=t("DIMMED"), padx=24, pady=7, cursor="hand2")
        cancel_btn.bind("<Button-1>", lambda e: dlg.destroy())
        cancel_btn.pack(side="left", padx=5)

        if on_delete:
            del_btn = tk.Label(btn_row, text="Excluir", font=(FONT, 12),
                               bg=t("RED_DIM"), fg=t("RED"), padx=24, pady=7, cursor="hand2")
            def do_del():
                if messagebox.askyesno("Excluir", f"Excluir esta missão?", parent=dlg):
                    on_delete()
                    dlg.destroy()
                    self._update_icon()
                    self._refresh_dashboard()
            del_btn.bind("<Button-1>", lambda e: do_del())
            del_btn.pack(side="left", padx=5)

        dlg.bind("<Return>", lambda e: do_save())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.mainloop()

    def _edit_goal(self, gi, g):
        def _do():
            def on_save(nm, amt, sd, ed):
                old = self.data["goals"][gi]["name"]
                self.data["goals"][gi] = {"name": nm, "amount": amt, "start_date": sd, "end_date": ed}
                if nm != old:
                    for k, v in self.data.get("goal_assignments", {}).items():
                        if v == old:
                            self.data["goal_assignments"][k] = nm
                save_data(self.data)

            def on_delete():
                self.data["goals"].pop(gi)
                save_data(self.data)

            self._goal_form(
                f"Editar — {g['name']}",
                {"name": g["name"], "amount": str(g["amount"]), "start_date": g["start_date"], "end_date": g["end_date"]},
                on_save, on_delete,
            )
        threading.Thread(target=_do, daemon=True).start()

    def _add_goal(self):
        def _do():
            def on_save(nm, amt, sd, ed):
                self.data.setdefault("goals", []).append({"name": nm, "amount": amt, "start_date": sd, "end_date": ed})
                save_data(self.data)

            self._goal_form(
                "Nova Missão",
                {"name": "", "amount": "", "start_date": date.today().isoformat(),
                 "end_date": (date.today() + timedelta(days=365)).isoformat()},
                on_save,
            )
        threading.Thread(target=_do, daemon=True).start()

    # ── Theme Toggle ──────────────────────────────────────────────────────────
    def _toggle_theme(self):
        current = self.data.get("settings", {}).get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self._apply_theme(new_theme)
        save_data(self.data)

        self._refresh_dashboard()
        if self.dashboard_window:
            self.dashboard_window.after(100, lambda: self._apply_titlebar_color(self.dashboard_window))

    # ── Export CSV ─────────────────────────────────────────────────────────────
    def _export_csv(self):
        win = self.dashboard_window
        if not win:
            return
        path = filedialog.asksaveasfilename(parent=win, defaultextension=".csv",
                                             filetypes=[("CSV", "*.csv")],
                                             initialfile="money_mission_export.csv")
        if not path:
            return
        asgn = self.data.get("goal_assignments", {})
        goals = self._goals()
        default_g = goals[0]["name"] if goals else ""
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Data", "Descrição", "Categoria", "Meta", "Tipo", "Valor"])
            for i, e in enumerate(self.data["entries"]):
                w.writerow([
                    e["timestamp"][:16].replace("T", " "),
                    e.get("description", ""),
                    e.get("category", "Outro"),
                    asgn.get(str(i), default_g),
                    e.get("type", "receita"),
                    e["amount"],
                ])
        messagebox.showinfo("Exportado", f"Salvo em:\n{path}", parent=win)

    # ── Auto Startup ──────────────────────────────────────────────────────────
    @staticmethod
    def _ensure_startup():
        try:
            startup_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            bat_path = os.path.join(startup_dir, "Missionfy.bat")
            if not os.path.exists(bat_path):
                exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
                if getattr(sys, 'frozen', False):
                    with open(bat_path, "w") as f:
                        f.write(f'@echo off\nstart "" "{exe}"\n')
                else:
                    with open(bat_path, "w") as f:
                        f.write(f'@echo off\nstart /min pythonw "{exe}"\n')
        except Exception:
            pass

    # ── Manage Categories ─────────────────────────────────────────────────────
    def _manage_categories(self):
        threading.Thread(target=self._manage_categories_dialog, daemon=True).start()

    def _manage_categories_dialog(self):
        dlg = tk.Tk()
        dlg.title("Gerenciar Categorias")
        dlg.configure(bg=t("BG"))
        dlg.geometry("400x480")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        set_window_icon(dlg)
        dlg.after(50, lambda: style_titlebar(dlg))

        tk.Label(dlg, text="Categorias", font=(FONT, 14, "bold"),
                 bg=t("BG"), fg=t("FG")).pack(pady=(18, 5))
        tk.Label(dlg, text="Adicione, renomeie ou remova categorias",
                 font=(FONT, 12), bg=t("BG"), fg=t("DIMMED")).pack(pady=(0, 10))

        cats = self.data.get("categories", DEFAULT_CATEGORIES)[:]
        list_frame = tk.Frame(dlg, bg=t("BG"))
        list_frame.pack(fill="both", expand=True, padx=25)

        def refresh_list():
            for w in list_frame.winfo_children():
                w.destroy()
            for i, cat in enumerate(cats):
                row_bg = t("BG_CARD") if i % 2 == 0 else t("BG2")
                row = tk.Frame(list_frame, bg=row_bg)
                row.pack(fill="x", pady=1)

                tk.Label(row, text=cat, font=(FONT, 12), bg=row_bg, fg=t("FG"),
                         padx=12, pady=6, anchor="w").pack(side="left", fill="x", expand=True)

                # Rename
                ren = tk.Label(row, text="Renomear", font=(FONT, 12), bg=t("BLUE_DIM"), fg=t("ACCENT2"),
                               padx=6, pady=3, cursor="hand2")
                ren.bind("<Button-1>", lambda e, idx=i: rename_cat(idx))
                ren.pack(side="left", padx=(0, 3), pady=3)

                # Delete
                dl = tk.Label(row, text="✕", font=(FONT, 12, "bold"), bg=t("RED_DIM"), fg=t("RED"),
                              padx=6, pady=3, cursor="hand2")
                dl.bind("<Button-1>", lambda e, idx=i: delete_cat(idx))
                dl.pack(side="left", padx=(0, 8), pady=3)

        def rename_cat(idx):
            # Inline rename
            for w in list_frame.winfo_children():
                w.destroy()
            for i, cat in enumerate(cats):
                row_bg = t("BG_CARD") if i % 2 == 0 else t("BG2")
                row = tk.Frame(list_frame, bg=row_bg)
                row.pack(fill="x", pady=1)
                if i == idx:
                    # Editable field
                    ent = tk.Entry(row, font=(FONT, 11), bg=t("BG_INPUT"), fg=t("FG"),
                                   insertbackground=t("FG"), relief="flat",
                                   highlightbackground=t("ACCENT"), highlightthickness=2)
                    ent.insert(0, cat)
                    ent.pack(fill="x", padx=12, pady=6, ipady=3)
                    ent.focus_set()
                    ent.select_range(0, tk.END)
                    def confirm(e=None, entry=ent, index=idx):
                        new_name = entry.get().strip()
                        if new_name:
                            old_name = cats[index]
                            cats[index] = new_name
                            for en in self.data["entries"]:
                                if en.get("category") == old_name:
                                    en["category"] = new_name
                        refresh_list()
                    ent.bind("<Return>", confirm)
                    ent.bind("<Escape>", lambda e: refresh_list())
                else:
                    tk.Label(row, text=cat, font=(FONT, 11), bg=row_bg, fg=t("FG"),
                             padx=12, pady=6).pack(side="left", fill="x", expand=True)

        def delete_cat(idx):
            if len(cats) <= 1:
                messagebox.showwarning("Aviso", "Precisa ter pelo menos uma categoria.", parent=dlg)
                return
            cats.pop(idx)
            refresh_list()

        def add_cat():
            # Inline input instead of simpledialog
            input_frame = tk.Frame(list_frame, bg=t("ACCENT"))
            input_frame.pack(fill="x", pady=1)
            new_entry = tk.Entry(input_frame, font=(FONT, 11), bg=t("BG_INPUT"), fg=t("FG"),
                                 insertbackground=t("FG"), relief="flat",
                                 highlightbackground=t("BORDER"), highlightthickness=1)
            new_entry.pack(fill="x", padx=12, pady=8, ipady=4)
            new_entry.focus_set()

            def confirm(e=None):
                name = new_entry.get().strip()
                if name and name not in cats:
                    cats.append(name)
                input_frame.destroy()
                refresh_list()

            new_entry.bind("<Return>", confirm)
            new_entry.bind("<Escape>", lambda e: (input_frame.destroy()))

        def save_all():
            self.data["categories"] = cats
            save_data(self.data)
            dlg.destroy()
            self._refresh_dashboard()

        refresh_list()

        # Bottom buttons
        btn_row = tk.Frame(dlg, bg=t("BG"))
        btn_row.pack(pady=(12, 15))

        add_btn = tk.Label(btn_row, text="+ Nova Categoria", font=(FONT, 12),
                           bg=t("GREEN_DIM"), fg=t("ACCENT"), padx=16, pady=6, cursor="hand2")
        add_btn.bind("<Button-1>", lambda e: add_cat())
        add_btn.pack(side="left", padx=5)

        save_btn = tk.Label(btn_row, text="Salvar", font=(FONT, 12),
                            bg=t("ACCENT"), fg=t("BG"), padx=20, pady=6, cursor="hand2")
        save_btn.bind("<Button-1>", lambda e: save_all())
        save_btn.pack(side="left", padx=5)

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.mainloop()

    # ── Settings (inline in dashboard) ───────────────────────────────────────
    def _draw_settings(self, parent):
        sec = tk.Frame(parent, bg=t("BG"))
        sec.pack(fill="x", padx=24, pady=(16, 6))
        tk.Label(sec, text="CONFIGURAÇÕES", font=(FONT, 10, "bold"),
                 bg=t("BG"), fg=t("DIMMED")).pack(side="left")

        card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        card.pack(fill="x", padx=24, pady=(0, 0))
        inner = tk.Frame(card, bg=t("BG_CARD"), padx=18, pady=14)
        inner.pack(fill="x")

        settings = self.data.get("settings", {})

        # ── Notificações ──────────────────────────────────────────────────
        tk.Label(inner, text="Notificações", font=(FONT, 12, "bold"),
                 bg=t("BG_CARD"), fg=t("ACCENT2")).pack(anchor="w", pady=(0, 8))

        # Intervalo - frequência
        tk.Label(inner, text="FREQUÊNCIA DO LEMBRETE", font=(FONT, 10),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(0, 4))

        freq_options = [
            ("30 min", 30),
            ("1 hora", 60),
            ("2 horas", 120),
            ("6 horas", 360),
            ("Diário", 1440),
            ("Semanal", 10080),
            ("Mensal", 43200),
        ]
        current_min = settings.get("reminder_min", 120)
        reminder_var = tk.IntVar(value=current_min)

        freq_row = tk.Frame(inner, bg=t("BG_CARD"))
        freq_row.pack(fill="x", pady=(0, 8))

        for label, mins in freq_options:
            is_sel = current_min == mins
            btn = tk.Label(freq_row, text=label, font=(FONT, 10),
                           bg=t("ACCENT2") if is_sel else t("BG_HOVER"),
                           fg=t("BG") if is_sel else t("FG"),
                           padx=10, pady=4, cursor="hand2")
            def select(e=None, b=btn, m=mins):
                reminder_var.set(m)
                for w in freq_row.winfo_children():
                    w.configure(bg=t("BG_HOVER"), fg=t("FG"))
                b.configure(bg=t("ACCENT2"), fg=t("BG"))
            btn.bind("<Button-1>", select)
            btn.pack(side="left", padx=(0, 4), pady=2)

        # Checkboxes
        notify_no_revenue = tk.BooleanVar(value=settings.get("notify_no_revenue", True))
        notify_daily_progress = tk.BooleanVar(value=settings.get("notify_daily_progress", True))
        notify_milestones = tk.BooleanVar(value=settings.get("notify_milestones", True))

        for var, text in [
            (notify_no_revenue, "Lembrar se não registrei receita hoje"),
            (notify_daily_progress, "Mostrar progresso diário"),
            (notify_milestones, "Avisar ao atingir marcos (25%, 50%, 75%, 100%)"),
        ]:
            cb = tk.Checkbutton(inner, text=text, variable=var, font=(FONT, 11),
                                bg=t("BG_CARD"), fg=t("FG"), selectcolor=t("BG_INPUT"),
                                activebackground=t("BG_CARD"), activeforeground=t("FG"),
                                highlightthickness=0)
            cb.pack(anchor="w", pady=1)

        # Salvar
        success_label = tk.Label(inner, text="", font=(FONT, 10), bg=t("BG_CARD"), fg=t("ACCENT"))
        success_label.pack(pady=(8, 0))

        def save_settings():
            rm = reminder_var.get()
            self.data.setdefault("settings", {}).update({
                "reminder_min": rm,
                "notify_no_revenue": notify_no_revenue.get(),
                "notify_daily_progress": notify_daily_progress.get(),
                "notify_milestones": notify_milestones.get(),
            })
            save_data(self.data)
            success_label.configure(text="✓ Configurações salvas!")
            success_label.after(3000, lambda: success_label.configure(text=""))

        save_row = tk.Frame(inner, bg=t("BG_CARD"))
        save_row.pack(fill="x", pady=(6, 0))
        save_btn = tk.Label(save_row, text="Salvar Configurações", font=(FONT, 11),
                            bg=t("ACCENT"), fg=t("BG"), padx=20, pady=6, cursor="hand2")
        save_btn.bind("<Button-1>", lambda e: save_settings())
        save_btn.bind("<Enter>", lambda e: save_btn.configure(bg=self._lighten(t("ACCENT"))))
        save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=t("ACCENT")))
        save_btn.pack(side="left")

    # ── Quit ──────────────────────────────────────────────────────────────────
    def _on_quit(self, icon, item):
        try:
            if self.dashboard_window and self.dashboard_window.winfo_exists():
                self.dashboard_window.destroy()
                self.dashboard_window = None
        except Exception:
            pass
        if HAS_KEYBOARD:
            try:
                kb.unhook_all()
            except Exception:
                pass
        icon.stop()

    # ── Reflection Dialog ─────────────────────────────────────────────────────
    def _show_reflection_dialog(self):
        dlg = tk.Tk()
        dlg.title("Reflexao da Semana")
        dlg.configure(bg=t("BG"))
        dlg.geometry("400x380")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        set_window_icon(dlg)
        dlg.after(50, lambda: style_titlebar(dlg))

        PAD = 24

        # Auto summary
        entries = self.data["entries"]
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_entries = [e for e in entries if e["timestamp"][:10] >= week_start.isoformat()]
        week_rev = sum(e["amount"] for e in week_entries if e["amount"] > 0)

        goal = self._main_goal()
        ents_goal = entries_for_goal(self.data, goal["name"])
        rev_goal = [e for e in ents_goal if e["amount"] > 0]
        total = sum(e["amount"] for e in rev_goal)
        remaining = max(goal["amount"] - total, 0)
        dl = days_left(goal)
        daily_needed = remaining / dl if dl > 0 else 0

        week_days_hit = 0
        for i in range(min(today.weekday() + 1, 7)):
            d = week_start + timedelta(days=i)
            day_total = sum(e["amount"] for e in rev_goal if e["amount"] > 0 and e["timestamp"][:10] == d.isoformat())
            if day_total >= daily_needed and daily_needed > 0:
                week_days_hit += 1

        tk.Label(dlg, text="Como foi sua semana?", font=(FONT, 16, "bold"),
                 bg=t("BG"), fg=t("FG")).pack(padx=PAD, pady=(20, 0), anchor="w")

        summary = f"Voce registrou R${week_rev:,.2f} esta semana"
        if daily_needed > 0:
            summary += f", bateu a meta {week_days_hit} de {min(today.weekday() + 1, 7)} dias"
        tk.Label(dlg, text=summary, font=(FONT, 10), bg=t("BG"), fg=t("DIMMED"),
                 wraplength=350).pack(padx=PAD, pady=(8, 16), anchor="w")

        # Feeling buttons
        selected = tk.StringVar(value="")
        feelings = [
            ("\U0001f604 Otima", "otima", t("ACCENT")),
            ("\U0001f642 Boa", "boa", t("YELLOW")),
            ("\U0001f610 Podia ser melhor", "podia_ser_melhor", t("RED")),
        ]
        feel_frame = tk.Frame(dlg, bg=t("BG"))
        feel_frame.pack(padx=PAD, fill="x")

        for text, val, color in feelings:
            btn = tk.Label(feel_frame, text=text, font=(FONT, 13),
                           bg=t("BG_CARD"), fg=t("FG"), padx=16, pady=10,
                           cursor="hand2", highlightbackground=t("BORDER"), highlightthickness=1)
            btn.pack(fill="x", pady=(0, 6))
            def select(e=None, v=val, b=btn, c=color):
                selected.set(v)
                for w in feel_frame.winfo_children():
                    w.configure(bg=t("BG_CARD"), highlightbackground=t("BORDER"))
                b.configure(bg=c, highlightbackground=c)
            btn.bind("<Button-1>", select)

        # Optional note
        tk.Label(dlg, text="Uma palavra sobre a semana (opcional)", font=(FONT, 10),
                 bg=t("BG"), fg=t("DIMMED")).pack(padx=PAD, pady=(12, 4), anchor="w")
        note_entry = tk.Entry(dlg, font=(FONT, 12), bg=t("BG_INPUT"), fg=t("FG"),
                              insertbackground=t("FG"), relief="flat",
                              highlightbackground=t("BORDER"), highlightthickness=1)
        note_entry.pack(padx=PAD, fill="x", ipady=5)

        def save_reflection():
            if not selected.get():
                return
            week_key = datetime.now().strftime("%Y-W%U")
            self.data.setdefault("reflections", []).append({
                "week": week_key,
                "feeling": selected.get(),
                "note": note_entry.get().strip(),
                "revenue": week_rev,
                "days_hit": week_days_hit,
                "timestamp": datetime.now().isoformat(),
            })
            save_data(self.data)
            self._try_refresh()
            dlg.destroy()

        save_btn = tk.Label(dlg, text="Salvar", font=(FONT, 12, "bold"),
                            bg=t("ACCENT"), fg="#12121a", padx=24, pady=10, cursor="hand2")
        save_btn.pack(padx=PAD, fill="x", pady=(16, 0))
        save_btn.bind("<Button-1>", lambda e: save_reflection())

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.mainloop()

    # ── Run ───────────────────────────────────────────────────────────────────
    def run(self):
        # Backup timer
        def backup_loop():
            while True:
                threading.Event().wait(BACKUP_INTERVAL_MIN * 60)
                try:
                    do_backup(self.data)
                except Exception:
                    pass
        threading.Thread(target=backup_loop, daemon=True).start()

        # Smart reminder timer
        def reminder_loop():
            while True:
                settings = self.data.get("settings", {})
                interval = settings.get("reminder_min", REMINDER_INTERVAL_MIN)
                threading.Event().wait(max(interval, 1) * 60)
                try:
                    if not self.icon:
                        continue
                    settings = self.data.get("settings", {})
                    entries = self.data["entries"]
                    today_rev = sum(e["amount"] for e in entries if e["amount"] > 0 and e["timestamp"][:10] == date.today().isoformat())
                    goal = self._main_goal()
                    total = self._main_total()
                    remaining = max(goal["amount"] - total, 0)
                    dl = days_left(goal)
                    daily_needed = remaining / dl if dl > 0 else 0

                    if today_rev == 0 and settings.get("notify_no_revenue", True):
                        self.icon.notify(
                            f"Você ainda não registrou receita hoje!\nPrecisa de R${daily_needed:,.2f}/dia para bater a meta.",
                            "Missionfy")
                    elif today_rev > 0 and today_rev < daily_needed and settings.get("notify_daily_progress", True):
                        falta = daily_needed - today_rev
                        self.icon.notify(
                            f"Hoje: R${today_rev:,.2f} — faltam R${falta:,.2f} para a meta diária.",
                            "Missionfy")
                except Exception:
                    pass
        threading.Thread(target=reminder_loop, daemon=True).start()

        # Global hotkey
        if HAS_KEYBOARD:
            try:
                kb.add_hotkey(HOTKEY, lambda: self._on_show_dashboard(None, None))
            except Exception:
                pass

        # Initial backup
        try:
            do_backup(self.data)
        except Exception:
            pass

        # Always ensure startup
        self._ensure_startup()

        # Pulse icon red when behind on daily target
        def pulse_loop():
            pulse_state = [False]
            while True:
                threading.Event().wait(3)
                try:
                    if not self.icon:
                        continue
                    gm = calc_gamification(self.data, self._main_goal())
                    if gm["is_behind"]:
                        pulse_state[0] = not pulse_state[0]
                        if pulse_state[0]:
                            self.icon.icon = create_icon_image(0.0)  # red icon
                        else:
                            self.icon.icon = create_icon_image(self._main_progress())
                    else:
                        pulse_state[0] = False
                        self.icon.icon = create_icon_image(self._main_progress())
                except Exception:
                    pass
        threading.Thread(target=pulse_loop, daemon=True).start()

        def reflection_loop():
            import time
            while True:
                now = datetime.now()
                # Sunday at 20:00
                if now.weekday() == 6 and now.hour == 20 and now.minute == 0:
                    week_key = now.strftime("%Y-W%U")
                    reflections = self.data.get("reflections", [])
                    already = any(r["week"] == week_key for r in reflections)
                    if not already:
                        # Try native notification
                        try:
                            from plyer import notification
                            notification.notify(
                                title="Missionfy - Reflexao da Semana",
                                message="Como foi sua semana? Clique pra avaliar",
                                app_icon=ICO_FILE if os.path.exists(ICO_FILE) else None,
                                timeout=10
                            )
                        except Exception:
                            pass
                        threading.Thread(target=self._show_reflection_dialog, daemon=True).start()
                time.sleep(60)
        threading.Thread(target=reflection_loop, daemon=True).start()

        self.icon = CustomIcon(
            "Missionfy",
            create_icon_image(self._main_progress()),
            title=f"Missionfy — {pct_label(self._main_total(), self._main_goal())}",
            menu=self._build_menu(),
            on_any_click=lambda: self._show_tray_popup(None),
            on_double_click=lambda: threading.Thread(target=self._show_dashboard, daemon=True).start(),
        )
        self.icon.run()


def show_splash():
    """Splash screen while app loads."""
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    splash.configure(bg="#0a0a0f")

    sw = splash.winfo_screenwidth()
    sh = splash.winfo_screenheight()
    w, h = 380, 220
    splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # Border
    border = tk.Frame(splash, bg="#2a2a38")
    border.pack(fill="both", expand=True, padx=1, pady=1)
    inner = tk.Frame(border, bg="#0a0a0f")
    inner.pack(fill="both", expand=True)

    # Icon
    try:
        if os.path.exists(ICON_FILE):
            from PIL import ImageTk
            ico = Image.open(ICON_FILE).resize((64, 64), Image.LANCZOS)
            photo = ImageTk.PhotoImage(ico)
            lbl = tk.Label(inner, image=photo, bg="#0a0a0f")
            lbl.image = photo
            lbl.pack(pady=(30, 10))
    except Exception:
        tk.Label(inner, text="$", font=(FONT, 32, "bold"), bg="#0a0a0f", fg="#00d47e").pack(pady=(30, 10))

    tk.Label(inner, text="Missionfy", font=(FONT, 18, "bold"),
             bg="#0a0a0f", fg="#f0f8f4").pack()
    tk.Label(inner, text="Carregando...", font=(FONT, 12),
             bg="#0a0a0f", fg="#7aaa95").pack(pady=(5, 0))

    # Progress bar animation
    bar_bg = tk.Frame(inner, bg="#1a1a28", height=4)
    bar_bg.pack(fill="x", padx=60, pady=(15, 0))
    bar_bg.pack_propagate(False)
    bar_fill = tk.Frame(bar_bg, bg="#00d47e", height=4, width=0)
    bar_fill.place(relx=0, rely=0, relwidth=0, relheight=1.0)

    steps = [0.0, 0.2, 0.5, 0.7, 0.9, 1.0]
    for i, pct_val in enumerate(steps):
        splash.after(i * 300, lambda p=pct_val: bar_fill.place(relwidth=p))

    splash.after(1800, splash.destroy)
    splash.mainloop()


def show_welcome_wizard():
    """First-run wizard with 3 steps."""
    BG_W = "#0a0a0f"
    CARD_W = "#161620"
    BORDER_W = "#2a2a38"
    FG_W = "#f0f8f4"
    DIM_W = "#7a8a95"
    ACC_W = "#00d47e"
    INPUT_W = "#0e0e14"

    result = {"completed": False}
    step = [1]  # mutable for closure
    data = {"name": "Minha Missão", "amount": "25000", "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=365)).isoformat()}

    wiz = tk.Tk()
    wiz.title("Missionfy")
    wiz.configure(bg=BG_W)

    sw = wiz.winfo_screenwidth()
    sh = wiz.winfo_screenheight()
    w, h = 560, 700
    wiz.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    wiz.resizable(False, False)
    wiz.attributes("-topmost", True)
    set_window_icon(wiz)
    wiz.after(50, lambda: style_titlebar(wiz))

    content = tk.Frame(wiz, bg=BG_W)
    content.pack(fill="both", expand=True)

    def draw_step():
        for widget in content.winfo_children():
            widget.destroy()

        def skip():
            save_data({
                "entries": [], "goal_assignments": {},
                "categories": DEFAULT_CATEGORIES,
                "settings": {"theme": "dark"},
                "goals": DEFAULT_GOALS,
            })
            result["completed"] = True
            wiz.destroy()

        # ── Header (sempre) ───────────────────────────────────────────────
        hdr = tk.Frame(content, bg=BG_W)
        hdr.pack(fill="x", padx=35, pady=(30, 0))

        try:
            if os.path.exists(ICON_FILE):
                from PIL import ImageTk
                ico = Image.open(ICON_FILE).resize((48, 48), Image.LANCZOS)
                photo = ImageTk.PhotoImage(ico)
                lbl = tk.Label(hdr, image=photo, bg=BG_W)
                lbl.image = photo
                lbl.pack()
        except Exception:
            pass

        tk.Label(hdr, text="Missionfy", font=(FONT, 20, "bold"),
                 bg=BG_W, fg=FG_W).pack(pady=(6, 0))

        # Step indicator
        dots = tk.Frame(hdr, bg=BG_W)
        dots.pack(pady=(10, 0))
        for i in range(1, 4):
            color = ACC_W if i == step[0] else BORDER_W
            tk.Label(dots, text="●" if i == step[0] else "○", font=(FONT, 10),
                     bg=BG_W, fg=color).pack(side="left", padx=4)
        step_row = tk.Frame(hdr, bg=BG_W)
        step_row.pack(fill="x", pady=(4, 0))
        tk.Label(step_row, text=f"Passo {step[0]} de 3", font=(FONT, 9),
                 bg=BG_W, fg=DIM_W).pack(side="left", expand=True)
        skip_btn = tk.Label(step_row, text="Pular →", font=(FONT, 9),
                            bg=BG_W, fg=DIM_W, cursor="hand2")
        skip_btn.bind("<Button-1>", lambda e: skip())
        skip_btn.bind("<Enter>", lambda e: skip_btn.configure(fg=ACC_W))
        skip_btn.bind("<Leave>", lambda e: skip_btn.configure(fg=DIM_W))
        skip_btn.pack(side="right")

        # ── Step 1: Nome ──────────────────────────────────────────────────
        if step[0] == 1:
            card = tk.Frame(content, bg=CARD_W, highlightbackground=BORDER_W, highlightthickness=1)
            card.pack(fill="x", padx=35, pady=(20, 0))
            inner = tk.Frame(card, bg=CARD_W, padx=24, pady=20)
            inner.pack(fill="x")

            tk.Label(inner, text="Como quer chamar sua missão?", font=(FONT, 14, "bold"),
                     bg=CARD_W, fg=FG_W).pack(pady=(0, 4))
            tk.Label(inner, text="Dê um nome para o seu objetivo financeiro.\nIsso te ajuda a manter o foco!",
                     font=(FONT, 10), bg=CARD_W, fg=DIM_W, justify="center").pack(pady=(0, 12))

            ex_frame = tk.Frame(inner, bg=CARD_W)
            ex_frame.pack(pady=(0, 12))
            for ex in ["Viagem", "Emergência", "Carro", "Casa"]:
                tk.Label(ex_frame, text=ex, font=(FONT, 9), bg=BORDER_W, fg=ACC_W,
                         padx=8, pady=3).pack(side="left", padx=3)

            name_entry = tk.Entry(inner, font=(FONT, 12), bg=INPUT_W, fg=FG_W,
                                  insertbackground=FG_W, relief="flat", justify="center",
                                  highlightbackground=BORDER_W, highlightthickness=1)
            name_entry.insert(0, data["name"])
            name_entry.pack(fill="x", ipady=6)
            name_entry.focus_set()
            name_entry.select_range(0, tk.END)

            def next_step(e=None):
                data["name"] = name_entry.get().strip() or "Minha Missão"
                step[0] = 2
                draw_step()

            name_entry.bind("<Return>", next_step)

            btn = tk.Label(content, text="Próximo →", font=(FONT, 12, "bold"),
                           bg=ACC_W, fg=BG_W, padx=20, pady=8, cursor="hand2", width=12)
            btn.bind("<Button-1>", next_step)
            btn.bind("<Enter>", lambda e: btn.configure(bg="#00e88e"))
            btn.bind("<Leave>", lambda e: btn.configure(bg=ACC_W))
            btn.pack(pady=(20, 0))

        # ── Step 2: Valor ─────────────────────────────────────────────────
        elif step[0] == 2:
            card = tk.Frame(content, bg=CARD_W, highlightbackground=BORDER_W, highlightthickness=1)
            card.pack(fill="x", padx=35, pady=(20, 0))
            inner = tk.Frame(card, bg=CARD_W, padx=24, pady=20)
            inner.pack(fill="x")

            tk.Label(inner, text="Quanto quer alcançar?", font=(FONT, 14, "bold"),
                     bg=CARD_W, fg=FG_W).pack(pady=(0, 4))
            tk.Label(inner, text="Digite o valor total da sua missão em reais.\nQualquer valor vale, o importante é começar!",
                     font=(FONT, 10), bg=CARD_W, fg=DIM_W, justify="center").pack(pady=(0, 12))

            examples = tk.Frame(inner, bg=CARD_W)
            examples.pack(pady=(0, 12))
            for ex in ["R$ 1.000", "R$ 10.000", "R$ 50.000", "R$ 100.000"]:
                tk.Label(examples, text=ex, font=(FONT, 9), bg=BORDER_W, fg=ACC_W,
                         padx=8, pady=3).pack(side="left", padx=3)

            amt_entry = tk.Entry(inner, font=(FONT, 12), bg=INPUT_W, fg=FG_W,
                                 insertbackground=FG_W, relief="flat", justify="center",
                                 highlightbackground=BORDER_W, highlightthickness=1)
            amt_val = data["amount"]
            try:
                num = int(float(str(amt_val).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")))
                amt_val = f"R$ {num:,}".replace(",", ".")
            except (ValueError, TypeError):
                pass
            amt_entry.insert(0, amt_val)
            amt_entry.pack(fill="x", ipady=6)
            amt_entry.focus_set()
            amt_entry.select_range(0, tk.END)

            def format_amt(e=None):
                val = amt_entry.get().strip().replace("R$", "").replace(" ", "").replace(".", "").replace(",", "")
                if not val:
                    return
                try:
                    num = int(val)
                    amt_entry.delete(0, tk.END)
                    amt_entry.insert(0, f"R$ {num:,}".replace(",", "."))
                except ValueError:
                    pass

            amt_entry.bind("<FocusOut>", format_amt)

            error = tk.Label(inner, text="", font=(FONT, 9), bg=CARD_W, fg="#ff6b6b")
            error.pack(anchor="w")

            def next_step(e=None):
                raw = amt_entry.get().strip().replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
                try:
                    float(raw)
                    data["amount"] = raw
                    step[0] = 3
                    draw_step()
                except ValueError:
                    error.configure(text="Digite um número válido.")

            amt_entry.bind("<Return>", next_step)

            btns = tk.Frame(content, bg=BG_W)
            btns.pack(pady=(20, 0))
            back = tk.Label(btns, text="← Voltar", font=(FONT, 12),
                            bg=BORDER_W, fg=DIM_W, padx=20, pady=8, cursor="hand2", width=10)
            back.bind("<Button-1>", lambda e: (step.__setitem__(0, 1), draw_step()))
            back.pack(side="left", padx=(0, 8))
            fwd = tk.Label(btns, text="Próximo →", font=(FONT, 12, "bold"),
                           bg=ACC_W, fg=BG_W, padx=20, pady=8, cursor="hand2", width=12)
            fwd.bind("<Button-1>", next_step)
            fwd.bind("<Enter>", lambda e: fwd.configure(bg="#00e88e"))
            fwd.bind("<Leave>", lambda e: fwd.configure(bg=ACC_W))
            fwd.pack(side="left")

        # ── Step 3: Datas ─────────────────────────────────────────────────
        elif step[0] == 3:
            hoje = date.today()
            card = tk.Frame(content, bg=CARD_W, highlightbackground=BORDER_W, highlightthickness=1)
            card.pack(fill="x", padx=35, pady=(20, 0))
            inner = tk.Frame(card, bg=CARD_W, padx=24, pady=18)
            inner.pack(fill="x")

            tk.Label(inner, text="Em quanto tempo quer alcançar?", font=(FONT, 14, "bold"),
                     bg=CARD_W, fg=FG_W).pack(pady=(0, 4))
            tk.Label(inner, text="Escolha um prazo ou defina uma data.",
                     font=(FONT, 10), bg=CARD_W, fg=DIM_W).pack(pady=(0, 10))

            shortcuts = tk.Frame(inner, bg=CARD_W)
            shortcuts.pack(pady=(0, 12))

            selected_end = tk.StringVar(value=data["end_date"])

            prazo_opts = [
                ("3 meses", 90), ("6 meses", 180), ("1 ano", 365), ("2 anos", 730),
            ]

            def set_prazo(dias):
                end = hoje + timedelta(days=dias)
                selected_end.set(end.isoformat())
                end_display.configure(text=f"{end.strftime('%d/%m/%Y')}  ({dias} dias)")
                for w in shortcuts.winfo_children():
                    w.configure(bg=BORDER_W, fg=DIM_W)

            for label, dias in prazo_opts:
                btn = tk.Label(shortcuts, text=label, font=(FONT, 11), bg=BORDER_W, fg=DIM_W,
                               padx=12, pady=5, cursor="hand2")
                def click(e=None, d=dias, b=btn):
                    set_prazo(d)
                    for w in shortcuts.winfo_children():
                        w.configure(bg=BORDER_W, fg=DIM_W)
                    b.configure(bg=ACC_W, fg=BG_W)
                btn.bind("<Button-1>", click)
                btn.pack(side="left", padx=(0, 6))

            # Datas (preenchidas)
            dates_row = tk.Frame(inner, bg=CARD_W)
            dates_row.pack(fill="x")

            # Início (fixo: hoje)
            start_f = tk.Frame(dates_row, bg=CARD_W)
            start_f.pack(side="left", expand=True, fill="x", padx=(0, 8))
            tk.Label(start_f, text="INÍCIO", font=(FONT, 9), bg=CARD_W, fg=DIM_W).pack()
            tk.Label(start_f, text=f"Hoje, {hoje.strftime('%d/%m/%Y')}", font=(FONT, 12, "bold"),
                     bg=CARD_W, fg=FG_W).pack(pady=(2, 0))

            # Limite
            end_f = tk.Frame(dates_row, bg=CARD_W)
            end_f.pack(side="left", expand=True, fill="x")
            tk.Label(end_f, text="LIMITE", font=(FONT, 9), bg=CARD_W, fg=DIM_W).pack()

            try:
                end_d = date.fromisoformat(data["end_date"])
                dias_diff = (end_d - hoje).days
                end_text = f"{end_d.strftime('%d/%m/%Y')}  ({dias_diff} dias)"
            except ValueError:
                end_text = data["end_date"]
            end_display = tk.Label(end_f, text=end_text, font=(FONT, 12, "bold"),
                                   bg=CARD_W, fg=ACC_W)
            end_display.pack(pady=(2, 0))

            # Data personalizada
            tk.Label(inner, text="Ou digite uma data personalizada:", font=(FONT, 9),
                     bg=CARD_W, fg=DIM_W).pack(pady=(12, 3))
            custom_row = tk.Frame(inner, bg=CARD_W)
            custom_row.pack()
            end_entry = tk.Entry(custom_row, font=(FONT, 12), bg=INPUT_W, fg=FG_W,
                                 insertbackground=FG_W, relief="flat", width=14, justify="center",
                                 highlightbackground=BORDER_W, highlightthickness=1)
            try:
                ed_init = date.fromisoformat(data["end_date"]).strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                ed_init = data["end_date"]
            end_entry.insert(0, ed_init)
            end_entry.pack(side="left", ipady=4)
            tk.Label(custom_row, text="(dd/mm/aaaa)", font=(FONT, 9),
                     bg=CARD_W, fg=DIM_W).pack(side="left", padx=(8, 0))

            def apply_custom(e=None):
                val = end_entry.get().strip()
                try:
                    # Aceitar dd/mm/aaaa ou aaaa-mm-dd
                    try:
                        d = datetime.strptime(val, "%d/%m/%Y").date()
                    except ValueError:
                        d = date.fromisoformat(val)
                    if d <= hoje:
                        error.configure(text="A data deve ser no futuro!")
                        return
                    selected_end.set(d.isoformat())
                    dias_diff = (d - hoje).days
                    end_display.configure(text=f"{d.strftime('%d/%m/%Y')}  ({dias_diff} dias)")
                    for w in shortcuts.winfo_children():
                        w.configure(bg=BORDER_W, fg=DIM_W)
                    error.configure(text="")
                except ValueError:
                    error.configure(text="Formato invalido. Use dd/mm/aaaa")

            end_entry.bind("<Return>", apply_custom)
            end_entry.bind("<FocusOut>", apply_custom)

            error = tk.Label(inner, text="", font=(FONT, 9), bg=CARD_W, fg="#ff6b6b")
            error.pack(pady=(6, 0))

            tk.Label(inner, text="Você pode alterar tudo depois pelo painel.",
                     font=(FONT, 9), bg=CARD_W, fg=DIM_W).pack(pady=(6, 0))

            def finish(e=None):
                ed = selected_end.get()
                try:
                    d = date.fromisoformat(ed)
                    if d <= hoje:
                        error.configure(text="A data deve ser no futuro!")
                        return
                except ValueError:
                    error.configure(text="Data inválida.")
                    return

                save_data({
                    "entries": [], "goal_assignments": {},
                    "categories": DEFAULT_CATEGORIES,
                    "settings": {"theme": "dark"},
                    "goals": [{"name": data["name"], "amount": float(data["amount"]),
                               "start_date": hoje.isoformat(), "end_date": ed}],
                })
                result["completed"] = True
                wiz.destroy()

            btns = tk.Frame(content, bg=BG_W)
            btns.pack(pady=(16, 0))
            back = tk.Label(btns, text="← Voltar", font=(FONT, 12),
                            bg=BORDER_W, fg=DIM_W, padx=20, pady=8, cursor="hand2", width=10)
            back.bind("<Button-1>", lambda e: (step.__setitem__(0, 2), draw_step()))
            back.pack(side="left", padx=(0, 8))
            done = tk.Label(btns, text="Começar! 🚀", font=(FONT, 12, "bold"),
                            bg=ACC_W, fg=BG_W, padx=20, pady=8, cursor="hand2", width=12)
            done.bind("<Button-1>", finish)
            done.bind("<Enter>", lambda e: done.configure(bg="#00e88e"))
            done.bind("<Leave>", lambda e: done.configure(bg=ACC_W))
            done.pack(side="left")

    draw_step()
    wiz.mainloop()
    return result["completed"]


FONT = "Poppins"
FONT_FALLBACK = "Segoe UI"

def load_fonts():
    """Register Poppins fonts for this process."""
    try:
        import ctypes
        fonts_dir = os.path.join(BUNDLE_DIR, "fonts")
        if not os.path.exists(fonts_dir):
            fonts_dir = os.path.join(SCRIPT_DIR, "fonts")
        if os.path.exists(fonts_dir):
            for f in os.listdir(fonts_dir):
                if f.endswith(".ttf"):
                    ctypes.windll.gdi32.AddFontResourceW(os.path.join(fonts_dir, f))
    except Exception:
        pass

    # Check if Poppins is available
    global FONT
    try:
        root = tk.Tk()
        root.withdraw()
        available = list(root.call("font", "families"))
        root.destroy()
        if "Poppins" not in available:
            FONT = FONT_FALLBACK
    except Exception:
        FONT = FONT_FALLBACK


if __name__ == "__main__":
    # Set AppUserModelID so Windows uses our icon in taskbar, not Python's
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Missionfy.App.1")
    except Exception:
        pass

    load_fonts()

    # Splash screen
    show_splash()

    # First-run wizard (only if no data file exists)
    first_run = not os.path.exists(DATA_FILE)
    if first_run:
        if not show_welcome_wizard():
            sys.exit(0)  # User closed the wizard

    app = Missionfy()

    # Auto-open dashboard after first setup
    if first_run:
        threading.Thread(target=lambda: (threading.Event().wait(1), app._show_dashboard()), daemon=True).start()

    app.run()
