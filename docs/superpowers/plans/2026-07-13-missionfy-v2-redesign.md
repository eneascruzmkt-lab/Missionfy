# Missionfy v2.0 Redesign - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign visual completo + 7 novas funcionalidades focadas em praticidade e evolucao pessoal.

**Architecture:** Arquivo unico `money_mission.py` (padrao existente). Novas funcionalidades adicionadas como metodos da classe `Missionfy`. Dados persistidos no mesmo `money_mission_data.json` com novos campos via `setdefault`. Nova dependencia `plyer` para notificacoes nativas do Windows.

**Tech Stack:** Python 3.11, tkinter, pystray, Pillow, plyer (notificacoes nativas)

---

## File Structure

- **Modify:** `money_mission.py` - arquivo principal (todas as mudancas)
- **No new files** - manter padrao single-file do projeto

---

### Task 1: Atualizar paleta de cores e tema dark refinado

**Files:**
- Modify: `money_mission.py:48-67` (THEMES dict)

- [ ] **Step 1: Atualizar o dicionario THEMES["dark"]**

Substituir os valores atuais pelos novos:

```python
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
```

- [ ] **Step 2: Atualizar style_titlebar para usar nova cor de fundo**

Em `style_titlebar()` (linha ~301), a comparacao `T["BG"] == "#0a0a0f"` precisa mudar para `T["BG"] == "#12121a"`.

- [ ] **Step 3: Testar visualmente**

Run: `python money_mission.py`
Verificar: fundo mais quente, verde mais suave, cards mais distintos do fundo.

- [ ] **Step 4: Commit**

```bash
git add money_mission.py
git commit -m "style: atualizar paleta dark para visual refinado"
```

---

### Task 2: Redesign do Dashboard - Layout scroll vertical sem abas

**Files:**
- Modify: `money_mission.py` - metodos `_draw_dashboard`, `_switch_tab`, remover tab bar

O dashboard atual usa abas (Inicio, Registrar, Missoes, Config). O novo layout e uma tela unica com scroll vertical e rodape fixo com 3 botoes.

- [ ] **Step 1: Reescrever `_draw_dashboard` com layout scroll vertical**

Substituir o metodo `_draw_dashboard` inteiro. Novo layout:
- Header: logo + nome + data (manter existente)
- Scroll area com secoes verticais:
  1. `_draw_seu_dia(frame)` - novo metodo
  2. `_draw_sua_semana(frame)` - novo metodo
  3. `_draw_sua_jornada(frame)` - novo metodo (placeholder por agora)
  4. `_draw_suas_metas(frame)` - adaptado do existente
- Rodape fixo (fora do scroll): 3 botoes - "Registrar", "Importar CSV", "Config"

```python
def _draw_dashboard(self, win):
    PAD = 24
    main = tk.Frame(win, bg=t("BG"))
    main.pack(fill="both", expand=True)

    # Header
    hdr = tk.Frame(main, bg=t("BG"))
    hdr.pack(fill="x", padx=PAD, pady=(12, 0))
    # ... (manter header existente com logo + data)

    # Separator
    tk.Frame(main, bg=t("BORDER"), height=1).pack(fill="x", padx=PAD, pady=(10, 0))

    # Scrollable content
    content_outer = tk.Frame(main, bg=t("BG"))
    content_outer.pack(fill="both", expand=True)
    # ... (manter canvas + scrollbar existente)

    # Draw sections
    self._draw_seu_dia(frame)
    self._draw_sua_semana(frame)
    self._draw_sua_jornada(frame)
    self._draw_suas_metas(frame)

    tk.Frame(frame, bg=t("BG"), height=10).pack()

    # Fixed footer (outside scroll)
    footer = tk.Frame(main, bg=t("BG_CARD"), pady=10)
    footer.pack(fill="x", side="bottom")
    # 3 botoes: Registrar, Importar CSV, Config
```

- [ ] **Step 2: Criar metodo `_draw_seu_dia`**

Secao "Seu Dia" no topo do dashboard:
- Numero grande com frase: "Faltam R$82 pra meta de hoje" ou "Meta do dia batida!"
- Barra de progresso do dia (grossa, 12px, cantos arredondados via canvas)
- Botao grande "Registrar" (abre dialog de registro)

```python
def _draw_seu_dia(self, parent):
    PAD = 24
    goal = self._main_goal()
    ents = entries_for_goal(self.data, goal["name"])
    revenue_entries = [e for e in ents if e["amount"] > 0]
    total = sum(e["amount"] for e in revenue_entries)
    remaining = max(goal["amount"] - total, 0)
    dl = days_left(goal)
    daily_needed = remaining / dl if dl > 0 else 0
    today_d = date.today().isoformat()
    today_rev = sum(e["amount"] for e in revenue_entries if e["timestamp"][:10] == today_d)
    today_remaining = max(daily_needed - today_rev, 0)
    day_progress = min(today_rev / daily_needed, 1.0) if daily_needed > 0 else 1.0

    card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
    card.pack(fill="x", padx=PAD, pady=(12, 0))
    inner = tk.Frame(card, bg=t("BG_CARD"), padx=20, pady=16)
    inner.pack(fill="x")

    tk.Label(inner, text="SEU DIA", font=(FONT, 10, "bold"),
             bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w")

    if today_rev >= daily_needed and daily_needed > 0:
        msg = "Meta do dia batida!"
        msg_color = t("ACCENT")
    elif daily_needed > 0:
        msg = f"Faltam R${today_remaining:,.2f} pra meta de hoje"
        msg_color = t("YELLOW")
    else:
        msg = "Nenhuma meta ativa"
        msg_color = t("DIMMED")

    tk.Label(inner, text=msg, font=(FONT, 20, "bold"),
             bg=t("BG_CARD"), fg=msg_color).pack(anchor="w", pady=(8, 0))

    # Day progress bar (thick)
    bar = tk.Frame(inner, bg=t("BAR_BG"), height=14)
    bar.pack(fill="x", pady=(12, 0))
    bar.pack_propagate(False)
    color = t("ACCENT") if day_progress >= 1.0 else (t("YELLOW") if day_progress >= 0.4 else t("RED"))
    if day_progress > 0:
        tk.Frame(bar, bg=color, height=14).place(relx=0, rely=0, relwidth=min(day_progress, 1.0), relheight=1.0)

    tk.Label(inner, text=f"R${today_rev:,.2f} de R${daily_needed:,.2f} hoje",
             font=(FONT, 10), bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(6, 0))
```

- [ ] **Step 3: Criar metodo `_draw_sua_semana`**

Secao "Sua Semana":
- 7 quadradinhos (Seg a Dom), coloridos conforme bateu a meta ou nao
- Streak em destaque ao lado

```python
def _draw_sua_semana(self, parent):
    PAD = 24
    goal = self._main_goal()
    ents = entries_for_goal(self.data, goal["name"])
    revenue_entries = [e for e in ents if e["amount"] > 0]
    total = sum(e["amount"] for e in revenue_entries)
    remaining = max(goal["amount"] - total, 0)
    dl = days_left(goal)
    daily_needed = remaining / dl if dl > 0 else 0

    gm = calc_gamification(self.data, goal)

    card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
    card.pack(fill="x", padx=PAD, pady=(8, 0))
    inner = tk.Frame(card, bg=t("BG_CARD"), padx=20, pady=16)
    inner.pack(fill="x")

    top = tk.Frame(inner, bg=t("BG_CARD"))
    top.pack(fill="x")
    tk.Label(top, text="SUA SEMANA", font=(FONT, 10, "bold"),
             bg=t("BG_CARD"), fg=t("DIMMED")).pack(side="left")
    if gm["streak"] > 0:
        tk.Label(top, text=f"🔥 {gm['streak']} dias seguidos", font=(FONT, 11, "bold"),
                 bg=t("BG_CARD"), fg=t("YELLOW")).pack(side="right")

    # Week squares
    days_frame = tk.Frame(inner, bg=t("BG_CARD"))
    days_frame.pack(fill="x", pady=(12, 0))
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    day_labels = ["S", "T", "Q", "Q", "S", "S", "D"]

    for i in range(7):
        d = week_start + timedelta(days=i)
        day_str = d.isoformat()
        day_total = sum(e["amount"] for e in revenue_entries if e["timestamp"][:10] == day_str)
        is_today = d == today
        is_future = d > today

        if is_future:
            sq_color = t("BG_HOVER")
        elif day_total >= daily_needed and daily_needed > 0:
            sq_color = t("ACCENT")
        elif d <= today:
            sq_color = t("RED_DIM")
        else:
            sq_color = t("BG_HOVER")

        day_f = tk.Frame(days_frame, bg=t("BG_CARD"))
        day_f.pack(side="left", expand=True, fill="x")
        tk.Label(day_f, text=day_labels[i], font=(FONT, 9),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack()
        sq = tk.Frame(day_f, bg=sq_color, width=36, height=36,
                      highlightbackground=t("ACCENT") if is_today else t("BORDER"),
                      highlightthickness=2 if is_today else 1)
        sq.pack(pady=(4, 0))
        sq.pack_propagate(False)
        if day_total > 0:
            tk.Label(sq, text=f"R${day_total:,.0f}", font=(FONT, 7),
                     bg=sq_color, fg=t("FG")).pack(expand=True)
```

- [ ] **Step 4: Criar metodo `_draw_suas_metas`**

Adaptacao do `_draw_goal_card` existente mas dentro de uma secao com titulo:

```python
def _draw_suas_metas(self, parent):
    PAD = 24
    sec = tk.Frame(parent, bg=t("BG"))
    sec.pack(fill="x", padx=PAD, pady=(16, 4))
    tk.Label(sec, text="SUAS METAS", font=(FONT, 10, "bold"),
             bg=t("BG"), fg=t("DIMMED")).pack(anchor="w")
    for goal in self._goals():
        self._draw_goal_card(parent, goal)
```

- [ ] **Step 5: Criar rodape fixo com 3 botoes**

Rodape fora do scroll, sempre visivel:

```python
# No _draw_dashboard, apos o scroll area:
footer = tk.Frame(main, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
footer.pack(fill="x", side="bottom")
footer_inner = tk.Frame(footer, bg=t("BG_CARD"), pady=8)
footer_inner.pack()

for icon_char, label, cmd in [
    ("+", "Registrar", lambda: self._on_add_revenue(None, None)),
    ("📥", "Importar CSV", lambda: self._show_csv_import()),
    ("⚙", "Config", lambda: self._show_config_window()),
]:
    btn = tk.Frame(footer_inner, bg=t("BG_CARD"), cursor="hand2", padx=20)
    btn.pack(side="left", padx=8)
    tk.Label(btn, text=icon_char, font=(FONT, 14), bg=t("BG_CARD"), fg=t("ACCENT")).pack()
    tk.Label(btn, text=label, font=(FONT, 9), bg=t("BG_CARD"), fg=t("DIMMED")).pack()
    btn.bind("<Button-1>", lambda e, c=cmd: c())
    for child in btn.winfo_children():
        child.bind("<Button-1>", lambda e, c=cmd: c())
```

- [ ] **Step 6: Remover sistema de abas e metodos obsoletos**

Remover: `_switch_tab`, tab bar no `_draw_dashboard`, `_current_tab`.
Manter: `_draw_tab_receitas` (renomear para uso no dialog), `_draw_history`, `_draw_settings`.

- [ ] **Step 7: Testar visualmente**

Run: `python money_mission.py`
Verificar: scroll vertical funciona, secoes aparecem na ordem, rodape fixo, sem abas.

- [ ] **Step 8: Commit**

```bash
git add money_mission.py
git commit -m "feat: redesign dashboard com layout scroll vertical e rodape fixo"
```

---

### Task 3: Redesign do Popup da Bandeja com registro rapido

**Files:**
- Modify: `money_mission.py` - metodo `_create_tray_popup`

- [ ] **Step 1: Reescrever `_create_tray_popup` com novo layout**

Novo popup com 3 areas:
1. Topo: resumo inteligente (frase + barra + streak)
2. Meio: campo de registro rapido + atalhos recorrentes
3. Rodape: "Abrir Painel" e "Sair"

```python
def _create_tray_popup(self, click_x=None, click_y=None):
    popup = tk.Tk()
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.configure(bg=t("BORDER"))

    screen_w = popup.winfo_screenwidth()
    screen_h = popup.winfo_screenheight()
    cx = click_x if click_x is not None else popup.winfo_pointerx()

    inner = tk.Frame(popup, bg=t("BG"))
    inner.pack(fill="both", expand=True, padx=1, pady=1)

    # ── Header ──
    hdr = tk.Frame(inner, bg=t("BG_CARD"), padx=16, pady=12)
    hdr.pack(fill="x")

    goal = self._main_goal()
    ents = entries_for_goal(self.data, goal["name"])
    revenue_entries = [e for e in ents if e["amount"] > 0]
    total = sum(e["amount"] for e in revenue_entries)
    remaining = max(goal["amount"] - total, 0)
    dl = days_left(goal)
    daily_needed = remaining / dl if dl > 0 else 0
    today_d = date.today().isoformat()
    today_rev = sum(e["amount"] for e in revenue_entries if e["timestamp"][:10] == today_d)
    today_remaining = max(daily_needed - today_rev, 0)
    progress = pct(total, goal)
    gm = calc_gamification(self.data, goal)

    # Smart message
    if today_rev >= daily_needed and daily_needed > 0:
        smart_msg = "Meta do dia batida!"
        smart_color = t("ACCENT")
    elif daily_needed > 0:
        smart_msg = f"Faltam R${today_remaining:,.2f} hoje"
        smart_color = t("YELLOW")
    else:
        smart_msg = f"{int(progress * 100)}% da meta"
        smart_color = t("ACCENT")

    brand = tk.Frame(hdr, bg=t("BG_CARD"))
    brand.pack(fill="x")
    # Logo + nome (manter padrao existente)
    try:
        if os.path.exists(ICON_FILE):
            from PIL import ImageTk
            ico = Image.open(ICON_FILE).resize((20, 20), Image.LANCZOS)
            photo = ImageTk.PhotoImage(ico)
            icon_lbl = tk.Label(brand, image=photo, bg=t("BG_CARD"))
            icon_lbl.image = photo
            icon_lbl.pack(side="left", padx=(0, 6))
    except Exception:
        pass
    tk.Label(brand, text="Missionfy", font=(FONT, 11, "bold"),
             bg=t("BG_CARD"), fg=t("FG")).pack(side="left")
    if gm["streak"] > 0:
        tk.Label(brand, text=f"🔥{gm['streak']}", font=(FONT, 10),
                 bg=t("BG_CARD"), fg=t("YELLOW")).pack(side="right")

    tk.Label(hdr, text=smart_msg, font=(FONT, 13, "bold"),
             bg=t("BG_CARD"), fg=smart_color).pack(anchor="w", pady=(6, 0))

    # Progress bar
    bar = tk.Frame(hdr, bg=t("BAR_BG"), height=6)
    bar.pack(fill="x", pady=(6, 0))
    bar.pack_propagate(False)
    bar_color = t("ACCENT") if progress >= 0.75 else (t("YELLOW") if progress >= 0.4 else t("RED"))
    if progress > 0:
        tk.Frame(bar, bg=bar_color, height=6).place(relx=0, rely=0, relwidth=min(progress, 1.0), relheight=1.0)

    # ── Quick register ──
    tk.Frame(inner, bg=t("BORDER"), height=1).pack(fill="x", padx=12, pady=6)

    reg = tk.Frame(inner, bg=t("BG"), padx=16, pady=4)
    reg.pack(fill="x")

    tipo_var = tk.StringVar(value="receita")
    tipo_frame = tk.Frame(reg, bg=t("BG"))
    tipo_frame.pack(fill="x", pady=(0, 6))

    def make_tipo_toggle(text, val, color):
        is_sel = tipo_var.get() == val
        btn = tk.Label(tipo_frame, text=text, font=(FONT, 10),
                       bg=color if is_sel else t("BG_HOVER"),
                       fg=t("BG") if is_sel else t("FG"),
                       padx=12, pady=3, cursor="hand2")
        def select(e=None):
            tipo_var.set(val)
            for w in tipo_frame.winfo_children():
                w.destroy()
            make_tipo_toggle("+ Receita", "receita", t("ACCENT"))
            make_tipo_toggle("- Despesa", "despesa", t("RED"))
        btn.bind("<Button-1>", select)
        btn.pack(side="left", padx=(0, 4))

    make_tipo_toggle("+ Receita", "receita", t("ACCENT"))
    make_tipo_toggle("- Despesa", "despesa", t("RED"))

    val_entry = tk.Entry(reg, font=(FONT, 14), bg=t("BG_INPUT"), fg=t("FG"),
                         insertbackground=t("FG"), relief="flat",
                         highlightbackground=t("BORDER"), highlightthickness=1)
    val_entry.pack(fill="x", ipady=5)
    val_entry.insert(0, "Valor em R$")
    val_entry.configure(fg=t("DIMMED"))
    def on_focus_in(e):
        if val_entry.get() == "Valor em R$":
            val_entry.delete(0, tk.END)
            val_entry.configure(fg=t("FG"))
    def on_focus_out(e):
        if not val_entry.get():
            val_entry.insert(0, "Valor em R$")
            val_entry.configure(fg=t("DIMMED"))
    val_entry.bind("<FocusIn>", on_focus_in)
    val_entry.bind("<FocusOut>", on_focus_out)

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

    # ── Shortcuts (atalhos recorrentes) ──
    shortcuts = self._get_shortcuts()
    if shortcuts:
        sc_frame = tk.Frame(reg, bg=t("BG"))
        sc_frame.pack(fill="x", pady=(6, 0))
        for sc in shortcuts[:4]:
            sc_label = f"{sc['description']} R${sc['amount']:,.0f}"
            sc_btn = tk.Label(sc_frame, text=sc_label, font=(FONT, 9),
                              bg=t("BG_HOVER"), fg=t("FG"), padx=8, pady=3, cursor="hand2")
            def do_shortcut(e=None, s=sc):
                entry = {
                    "amount": s["amount"], "description": s["description"],
                    "category": s["category"], "type": "receita",
                    "timestamp": datetime.now().isoformat(),
                }
                self.data["entries"].append(entry)
                goals = self._goals()
                if goals:
                    self.data["goal_assignments"][str(len(self.data["entries"]) - 1)] = goals[0]["name"]
                save_data(self.data)
                self._update_icon()
                self._try_refresh()
                popup.destroy()
            sc_btn.bind("<Button-1>", do_shortcut)
            sc_btn.pack(side="left", padx=(0, 4))

    # ── Actions ──
    tk.Frame(inner, bg=t("BORDER"), height=1).pack(fill="x", padx=12, pady=6)

    def make_action(icon_char, label, cmd, fg_c=None):
        fg_c = fg_c or t("FG")
        btn = tk.Frame(inner, bg=t("BG"), cursor="hand2")
        btn.pack(fill="x")
        lbl_icon = tk.Label(btn, text=icon_char, font=(FONT, 12), bg=t("BG"), fg=fg_c, width=3)
        lbl_icon.pack(side="left", padx=(12, 0), pady=5)
        lbl_text = tk.Label(btn, text=label, font=(FONT, 12), bg=t("BG"), fg=fg_c, anchor="w")
        lbl_text.pack(side="left", fill="x", expand=True, pady=5)
        def enter(e):
            for w in [btn, lbl_icon, lbl_text]:
                w.configure(bg=t("BG_HOVER"))
        def leave(e):
            for w in [btn, lbl_icon, lbl_text]:
                w.configure(bg=t("BG"))
        def click(e):
            popup.destroy()
            cmd(self.icon, None)
        for w in (btn, lbl_icon, lbl_text):
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
            w.bind("<Button-1>", click)

    make_action("◻", "Ver Painel", self._on_show_dashboard, t("ACCENT2"))
    tk.Frame(inner, bg=t("BORDER"), height=1).pack(fill="x", padx=12, pady=6)
    make_action("✕", "Sair", self._on_quit, t("RED"))

    # Position
    popup.update_idletasks()
    pw = max(popup.winfo_reqwidth(), 320)
    ph = popup.winfo_reqheight()
    taskbar_h = max(screen_h - popup.winfo_screenheight(), 48)
    taskbar_h = max(taskbar_h, 48)
    final_x = max(5, min(cx - pw // 2, screen_w - pw - 5))
    final_y = screen_h - taskbar_h - ph - 8
    popup.geometry(f"{pw}x{ph}+{final_x}+{final_y}")

    popup.bind("<Escape>", lambda e: popup.destroy())
    popup.bind("<FocusOut>", lambda e: popup.destroy())
    popup.focus_force()
    val_entry.focus_set()
    popup.mainloop()
```

- [ ] **Step 2: Testar popup**

Run: `python money_mission.py`
Clicar no icone da bandeja. Verificar: resumo inteligente, campo de registro, atalhos.

- [ ] **Step 3: Commit**

```bash
git add money_mission.py
git commit -m "feat: redesign popup da bandeja com registro rapido e resumo inteligente"
```

---

### Task 4: Sistema de atalhos recorrentes

**Files:**
- Modify: `money_mission.py` - novos metodos `_get_shortcuts`, `_get_fixed_shortcuts`, secao no config

- [ ] **Step 1: Adicionar campo shortcuts no load_data**

Em `load_data()`, adicionar:
```python
data.setdefault("fixed_shortcuts", [])
data.setdefault("category_rules", {})
```

- [ ] **Step 2: Criar metodo `_get_shortcuts`**

```python
def _get_shortcuts(self):
    """Retorna ate 4 atalhos: fixados + automaticos dos mais frequentes."""
    fixed = self.data.get("fixed_shortcuts", [])
    if len(fixed) >= 4:
        return fixed[:4]

    # Auto: analisar ultimos 30 registros
    entries = [e for e in self.data["entries"] if e["amount"] > 0][-30:]
    freq = defaultdict(lambda: {"count": 0, "amount": 0, "description": "", "category": ""})
    for e in entries:
        key = f"{e.get('description', '')}_{e['amount']}"
        freq[key]["count"] += 1
        freq[key]["amount"] = e["amount"]
        freq[key]["description"] = e.get("description", "")
        freq[key]["category"] = e.get("category", "Outro")

    auto = sorted(freq.values(), key=lambda x: -x["count"])
    auto = [s for s in auto if s["count"] >= 2]  # minimo 2 vezes

    # Combinar fixados + auto, sem duplicar
    fixed_descs = {s["description"] for s in fixed}
    combined = list(fixed)
    for s in auto:
        if s["description"] not in fixed_descs and len(combined) < 4:
            combined.append(s)

    return combined[:4]
```

- [ ] **Step 3: Adicionar secao "Atalhos Rapidos" no config**

No metodo de config (sera criado como `_show_config_window`), adicionar secao para gerenciar atalhos fixos: adicionar, editar, remover.

- [ ] **Step 4: Testar atalhos**

Run: `python money_mission.py`
Registrar a mesma entrada 3x. Verificar que aparece como atalho no popup.

- [ ] **Step 5: Commit**

```bash
git add money_mission.py
git commit -m "feat: sistema de atalhos recorrentes com aprendizado automatico"
```

---

### Task 5: Secao "Sua Jornada" com grafico e linha do tempo

**Files:**
- Modify: `money_mission.py` - metodo `_draw_sua_jornada`

- [ ] **Step 1: Criar metodo `_draw_sua_jornada`**

Secao com:
1. Grafico de evolucao semana a semana (ultimas 8 semanas) usando Canvas
2. Marcos conquistados na linha do tempo
3. Historico de reflexoes (se houver)

```python
def _draw_sua_jornada(self, parent):
    PAD = 24
    entries = [e for e in self.data["entries"] if e["amount"] > 0]
    if not entries:
        return

    sec = tk.Frame(parent, bg=t("BG"))
    sec.pack(fill="x", padx=PAD, pady=(16, 4))
    tk.Label(sec, text="SUA JORNADA", font=(FONT, 10, "bold"),
             bg=t("BG"), fg=t("DIMMED")).pack(anchor="w")

    # Weekly evolution chart
    card = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
    card.pack(fill="x", padx=PAD, pady=(4, 0))

    cw, ch = 500, 180
    c = tk.Canvas(card, width=cw, height=ch, bg=t("BG_CARD"), highlightthickness=0)
    c.pack(padx=12, pady=12)

    # Agrupar por semana (ultimas 8)
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

    # Grid + bars
    for i, w in enumerate(weeks):
        x = pl + (i / max(len(weeks) - 1, 1)) * pw
        y_top = pt + ph * (1 - w["total"] / (max_val * 1.15))
        y_bot = pt + ph

        # Bar
        bar_w = pw / len(weeks) * 0.6
        c.create_rectangle(x - bar_w/2, y_top, x + bar_w/2, y_bot,
                          fill=t("ACCENT"), outline="")

        # Label
        label = w["start"].strftime("%d/%m")
        c.create_text(x, ch - 8, text=label, fill=t("DIMMED"), font=(FONT, 7))

        # Value on top
        if w["total"] > 0:
            c.create_text(x, y_top - 10, text=f"R${w['total']:,.0f}",
                         fill=t("FG"), font=(FONT, 7))

    # ── Marcos na linha do tempo ──
    milestones = self._get_earned_milestones()
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

    # ── Reflexoes semanais ──
    reflections = self.data.get("reflections", [])
    if reflections:
        ref_frame = tk.Frame(parent, bg=t("BG_CARD"), highlightbackground=t("BORDER"), highlightthickness=1)
        ref_frame.pack(fill="x", padx=PAD, pady=(4, 0))
        ref_inner = tk.Frame(ref_frame, bg=t("BG_CARD"), padx=16, pady=10)
        ref_inner.pack(fill="x")
        tk.Label(ref_inner, text="SUAS REFLEXOES", font=(FONT, 9, "bold"),
                 bg=t("BG_CARD"), fg=t("DIMMED")).pack(anchor="w", pady=(0, 6))

        feelings = {"otima": "😄", "boa": "🙂", "podia_ser_melhor": "😐"}
        for r in reflections[-4:]:
            rf = tk.Frame(ref_inner, bg=t("BG_CARD"))
            rf.pack(fill="x", pady=2)
            emoji = feelings.get(r.get("feeling", ""), "")
            tk.Label(rf, text=f"{emoji} Semana de {r['week']}", font=(FONT, 10),
                     bg=t("BG_CARD"), fg=t("FG")).pack(side="left")
            if r.get("note"):
                tk.Label(rf, text=f"- {r['note']}", font=(FONT, 9),
                         bg=t("BG_CARD"), fg=t("DIMMED")).pack(side="left", padx=(8, 0))
```

- [ ] **Step 2: Testar jornada**

Run: `python money_mission.py`
Verificar: grafico de barras semanal, marcos, reflexoes (se houver dados).

- [ ] **Step 3: Commit**

```bash
git add money_mission.py
git commit -m "feat: secao Sua Jornada com grafico semanal e marcos"
```

---

### Task 6: Marcos pessoais (milestones)

**Files:**
- Modify: `money_mission.py` - constantes + metodo `_get_earned_milestones`

- [ ] **Step 1: Adicionar constantes de marcos**

```python
MILESTONES = [
    # (id, nome, icone, tipo, valor)
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
```

- [ ] **Step 2: Criar metodo `_get_earned_milestones`**

```python
def _get_earned_milestones(self):
    entries = self.data.get("entries", [])
    revenue = [e for e in entries if e["amount"] > 0]
    total_rev = sum(e["amount"] for e in revenue)
    gm = calc_gamification(self.data, self._main_goal())

    # Dias unicos com uso
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
            # Calcular meses acima da meta (simplificado)
            unlocked = False  # implementar com dados mensais
        if unlocked:
            earned.append((icon, name))
    return earned
```

- [ ] **Step 3: Integrar notificacao ao desbloquear marco**

No metodo `save()` de registro de entrada, apos salvar, verificar se desbloqueou novo marco e notificar via `plyer`:

```python
# Apos salvar entrada:
old_milestones = set(m[1] for m in self._get_earned_milestones())
# ... salvar entrada ...
new_milestones = set(m[1] for m in self._get_earned_milestones())
newly_earned = new_milestones - old_milestones
if newly_earned:
    try:
        from plyer import notification
        for name in newly_earned:
            notification.notify(
                title="Missionfy - Novo Marco!",
                message=f"Voce desbloqueou: {name}",
                app_icon=ICO_FILE if os.path.exists(ICO_FILE) else None,
                timeout=5
            )
    except Exception:
        pass
```

- [ ] **Step 4: Testar marcos**

Run: `python money_mission.py`
Registrar entradas ate atingir R$100. Verificar notificacao + marco na jornada.

- [ ] **Step 5: Commit**

```bash
git add money_mission.py
git commit -m "feat: marcos pessoais com notificacao nativa ao desbloquear"
```

---

### Task 7: Importacao de CSV com categorizacao automatica

**Files:**
- Modify: `money_mission.py` - metodo `_show_csv_import` + parsers de banco

- [ ] **Step 1: Adicionar campo category_rules no load_data**

Ja adicionado na Task 4, Step 1: `data.setdefault("category_rules", {})`

- [ ] **Step 2: Criar parsers para cada banco**

```python
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
```

- [ ] **Step 3: Criar metodo `_categorize_entry`**

```python
DEFAULT_CATEGORY_KEYWORDS = {
    "salario": "Salario", "pagamento": "Salario",
    "pix recebido": "Freelance", "freelance": "Freelance",
    "investimento": "Investimento", "rendimento": "Investimento",
    "mercado": "Despesa", "farmacia": "Despesa", "uber": "Despesa",
    "transferencia": "Outro",
}

def _categorize_entry(self, description):
    """Categoriza uma entrada por descricao. Usa regras aprendidas primeiro, depois keywords."""
    desc_lower = description.lower().strip()

    # Regras aprendidas (prioridade)
    rules = self.data.get("category_rules", {})
    for keyword, category in rules.items():
        if keyword.lower() in desc_lower:
            return category

    # Keywords padrao
    for keyword, category in DEFAULT_CATEGORY_KEYWORDS.items():
        if keyword in desc_lower:
            return category

    return "Outro"
```

- [ ] **Step 4: Criar metodo `_show_csv_import`**

Dialog com 3 passos:
1. Escolher banco (4 botoes)
2. Selecionar arquivo + preview
3. Revisar categorias + confirmar

```python
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

        banks = [
            ("Picpay", "picpay"),
            ("Banco do Brasil", "banco_do_brasil"),
            ("Nubank", "nubank"),
            ("Bradesco", "bradesco"),
        ]
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

        def choose_file():
            path = filedialog.askopenfilename(
                title="Escolher CSV",
                filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
            )
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
                            amt_str = amt_str.replace("R$", "").replace(".", "").replace(",", ".")
                            amount = float(amt_str)
                            dt = datetime.strptime(date_str, parser["date_format"])
                            category = self._categorize_entry(desc)
                            parsed.append({
                                "amount": amount,
                                "description": desc,
                                "category": category,
                                "type": "receita" if amount >= 0 else "despesa",
                                "timestamp": dt.isoformat(),
                            })
                        except (ValueError, KeyError):
                            continue
                    self._csv_entries = parsed
                    self._csv_step = 3
                    draw_step()
            except Exception as ex:
                tk.Label(content, text=f"Erro ao ler arquivo: {ex}", font=(FONT, 10),
                         bg=t("BG"), fg=t("RED")).pack(pady=10)

        btn = tk.Label(content, text="Escolher arquivo CSV", font=(FONT, 13, "bold"),
                       bg=t("ACCENT"), fg=t("BG"), padx=24, pady=12, cursor="hand2")
        btn.pack(fill="x", pady=10)
        btn.bind("<Button-1>", lambda e: choose_file())

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

        canvas = tk.Canvas(list_frame, bg=t("BG"), highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=t("BG"))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        cats = self.data.get("categories", DEFAULT_CATEGORIES) + ["Outro"]

        for i, entry in enumerate(self._csv_entries[:50]):  # Limitar preview
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

            # Category dropdown (muda a categoria e salva regra)
            cat_var = tk.StringVar(value=entry["category"])
            cat_menu = ttk.Combobox(row, textvariable=cat_var, values=cats,
                                    width=10, state="readonly")
            cat_menu.pack(side="left", padx=4, pady=3)
            def on_cat_change(e=None, idx=i, var=cat_var, desc=entry["description"]):
                self._csv_entries[idx]["category"] = var.get()
                # Aprender regra
                key = desc.strip()
                if key:
                    self.data.setdefault("category_rules", {})[key] = var.get()
            cat_menu.bind("<<ComboboxSelected>>", on_cat_change)

        # Confirm button
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
                          font=(FONT, 12, "bold"), bg=t("ACCENT"), fg=t("BG"),
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
```

- [ ] **Step 5: Testar importacao**

Run: `python money_mission.py`
Criar um CSV de teste, importar, verificar categorias sugeridas, corrigir uma, reimportar e ver se aprendeu.

- [ ] **Step 6: Commit**

```bash
git add money_mission.py
git commit -m "feat: importacao de CSV com parser por banco e categorizacao automatica"
```

---

### Task 8: Reflexao semanal com notificacao nativa

**Files:**
- Modify: `money_mission.py` - instalar plyer, loop de reflexao, dialog

- [ ] **Step 1: Adicionar campo reflections no load_data**

```python
data.setdefault("reflections", [])
```

- [ ] **Step 2: Instalar plyer**

Run: `pip install plyer`

- [ ] **Step 3: Criar loop de reflexao semanal**

No metodo `run()`, adicionar thread que checa todo domingo as 20h:

```python
def reflection_loop():
    while True:
        now = datetime.now()
        if now.weekday() == 6 and now.hour == 20 and now.minute == 0:
            # Verificar se ja respondeu esta semana
            week_key = now.strftime("%Y-W%U")
            reflections = self.data.get("reflections", [])
            already = any(r["week"] == week_key for r in reflections)
            if not already:
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
                # Abrir dialog apos notificacao
                threading.Thread(target=self._show_reflection_dialog, daemon=True).start()
        import time
        time.sleep(60)

threading.Thread(target=reflection_loop, daemon=True).start()
```

- [ ] **Step 4: Criar dialog de reflexao**

```python
def _show_reflection_dialog(self):
    dlg = tk.Tk()
    dlg.title("Reflexao da Semana")
    dlg.configure(bg=t("BG"))
    dlg.geometry("400x350")
    dlg.resizable(False, False)
    dlg.attributes("-topmost", True)
    set_window_icon(dlg)
    dlg.after(50, lambda: style_titlebar(dlg))

    PAD = 24

    # Resumo automatico
    entries = self.data["entries"]
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_entries = [e for e in entries if e["timestamp"][:10] >= week_start.isoformat()]
    week_rev = sum(e["amount"] for e in week_entries if e["amount"] > 0)
    week_days_hit = 0
    goal = self._main_goal()
    ents_goal = entries_for_goal(self.data, goal["name"])
    rev_goal = [e for e in ents_goal if e["amount"] > 0]
    total = sum(e["amount"] for e in rev_goal)
    remaining = max(goal["amount"] - total, 0)
    dl = days_left(goal)
    daily_needed = remaining / dl if dl > 0 else 0

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
        ("😄 Otima", "otima", t("ACCENT")),
        ("🙂 Boa", "boa", t("YELLOW")),
        ("😐 Podia ser melhor", "podia_ser_melhor", t("RED")),
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

    # Note
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
                        bg=t("ACCENT"), fg=t("BG"), padx=24, pady=10, cursor="hand2")
    save_btn.pack(padx=PAD, fill="x", pady=(16, 0))
    save_btn.bind("<Button-1>", lambda e: save_reflection())

    dlg.bind("<Escape>", lambda e: dlg.destroy())
    dlg.mainloop()
```

- [ ] **Step 5: Testar reflexao**

Run: `python money_mission.py`
Chamar `_show_reflection_dialog` manualmente pra testar o dialog e salvar uma reflexao.

- [ ] **Step 6: Commit**

```bash
git add money_mission.py
git commit -m "feat: reflexao semanal com notificacao nativa e historico"
```

---

### Task 9: Janela de Config separada

**Files:**
- Modify: `money_mission.py` - metodo `_show_config_window`

- [ ] **Step 1: Criar metodo `_show_config_window`**

Janela separada (nao mais aba) com:
- Tema (dark/light toggle)
- Notificacoes (intervalo)
- Atalhos rapidos (gerenciar fixados)
- Historico de entradas
- Exportar CSV
- Sobre

Reutilizar `_draw_history` e `_draw_settings` existentes dentro de um novo dialog.

```python
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

    # Reutilizar metodos existentes
    self._draw_settings(frame)
    self._draw_history(frame)

    tk.Frame(frame, bg=t("BG"), height=20).pack()
    dlg.bind("<Escape>", lambda e: dlg.destroy())
    dlg.mainloop()
```

- [ ] **Step 2: Testar config**

Run: `python money_mission.py`
Clicar "Config" no rodape do dashboard. Verificar que abre janela separada.

- [ ] **Step 3: Commit**

```bash
git add money_mission.py
git commit -m "feat: janela de config separada do dashboard"
```

---

### Task 10: Calendario visual do streak (tipo GitHub)

**Files:**
- Modify: `money_mission.py` - adicionar ao `_draw_sua_jornada`

- [ ] **Step 1: Adicionar calendario de 30 dias no `_draw_sua_jornada`**

Apos o grafico semanal, adicionar grid de quadradinhos dos ultimos 30 dias:

```python
# Dentro de _draw_sua_jornada, apos o grafico:
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

    if d > today:
        color = t("BG_HOVER")
    elif day_total >= daily_needed and daily_needed > 0:
        color = t("ACCENT")
    elif day_total > 0:
        color = t("YELLOW")
    else:
        color = t("BAR_BG")

    row, col = divmod(i, 10)
    sq = tk.Frame(grid, bg=color, width=20, height=20,
                  highlightbackground=t("BORDER"), highlightthickness=1)
    sq.grid(row=row, column=col, padx=2, pady=2)
    sq.grid_propagate(False)
```

- [ ] **Step 2: Testar calendario**

Run: `python money_mission.py`
Verificar grid de quadradinhos com cores corretas.

- [ ] **Step 3: Commit**

```bash
git add money_mission.py
git commit -m "feat: calendario visual de 30 dias tipo GitHub na secao Jornada"
```

---

### Task 11: Ajustes finais e dependencias

**Files:**
- Modify: `money_mission.py` - imports, ajustes

- [ ] **Step 1: Adicionar import do plyer no topo do arquivo**

```python
try:
    from plyer import notification as plyer_notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False
```

- [ ] **Step 2: Atualizar comando PyInstaller**

Adicionar `plyer` como hidden import:

```bash
pyinstaller --onefile --noconsole --name "Missionfy" --icon="money_mission.ico" --add-data "icon.png;." --add-data "money_mission.ico;." --add-data "fonts;fonts" --hidden-import plyer.platforms.win.notification money_mission.py
```

- [ ] **Step 3: Testar build do .exe**

Run: `pip install plyer && pyinstaller ...`
Verificar que o .exe abre e funciona.

- [ ] **Step 4: Testar fluxo completo**

1. Abrir app
2. Clicar no icone da bandeja - popup com registro rapido
3. Registrar entrada pelo popup
4. Abrir painel - scroll vertical com Seu Dia, Sua Semana, Sua Jornada, Suas Metas
5. Importar CSV
6. Verificar marcos e medalhas
7. Abrir config

- [ ] **Step 5: Commit final**

```bash
git add money_mission.py
git commit -m "feat: Missionfy v2.0 - redesign completo com novas funcionalidades"
```
