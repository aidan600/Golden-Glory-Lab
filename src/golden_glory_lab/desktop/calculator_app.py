"""Ordinary-user Golden Glory Calculator desktop shell."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import ttk
from typing import Callable

from golden_glory_lab.desktop.breakdown_icons import (
    JEWEL_ICON_NAME,
    SLOT_ICON_NAMES,
    load_icon,
)
from golden_glory_lab.domain.flame_link import load_flame_link_level_table
from golden_glory_lab.domain.manual_calculator import (
    FIXED_LIGHT_RADIUS_SLOTS,
    INITIAL_JEWEL_COUNT,
    LightRadiusBreakdown,
    ManualCalculatorInput,
    default_manual_calculator_input,
    evaluate_manual_calculator,
)

WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 856
MAXIMUM_JEWEL_ROWS = 10

_BG = "#FFFFFF"
_PANEL = "#FFFFFF"
_BORDER = "#E4DDCE"
_RULE = "#EFEBE3"
_TAB_IDLE = "#F3EFE7"
_TEXT = "#23262B"
_MUTED = "#6B7078"
_GOLD = "#B0862E"
_GOLD_DEEP = "#8F6C1E"
_GOLD_SOFT = "#FCF7EA"
_GOLD_EDGE = "#EADFC2"
_FLAME = "#C2551F"
_ENMITY = "#A6362F"
_ERROR = "#9A3B2A"
_FIELD_BORDER = "#D5CEC1"
_HOVER = "#F6F2E9"

_F_PAGE_TITLE = ("Segoe UI Semibold", 15)
_F_SECTION = ("Segoe UI Semibold", 11)
_F_BODY = ("Segoe UI", 10)
_F_SMALL = ("Segoe UI", 9)
_F_BUTTON = ("Segoe UI Semibold", 10)
_F_RESULT_LABEL = ("Segoe UI", 10)
_F_RESULT_VALUE = ("Segoe UI Semibold", 22)
_F_TOTAL_LABEL = ("Segoe UI Semibold", 12)
_F_TOTAL_VALUE = ("Segoe UI Semibold", 26)

_GUTTER = 18
_DASH = "—"


class GoldenGloryCalculatorApp(tk.Tk):
    """Manual-first two-page calculator shell for ordinary users."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Golden Glory Calculator")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.configure(background=_BG)

        self._level_table = load_flame_link_level_table()
        self._breakdown = LightRadiusBreakdown()
        self._jewel_vars: list[tk.StringVar] = []
        self._icons: dict[str, tk.PhotoImage] = {}
        self._updating = False

        self._configure_styles()
        self._build()
        self._recalculate()

        window_icon = self._icon("sun_large")
        if window_icon is not None:
            try:
                self.iconphoto(False, window_icon)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------ setup

    def _icon(self, name: str) -> tk.PhotoImage | None:
        if name not in self._icons:
            photo = load_icon(self, name)
            if photo is None:
                return None
            self._icons[name] = photo
        return self._icons[name]

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=_BG, foreground=_TEXT, font=_F_BODY)
        style.configure("TFrame", background=_BG)

        style.configure(
            "Field.TEntry",
            fieldbackground="#FFFFFF",
            background="#FFFFFF",
            foreground=_TEXT,
            bordercolor=_FIELD_BORDER,
            lightcolor=_FIELD_BORDER,
            darkcolor=_FIELD_BORDER,
            borderwidth=1,
            relief="solid",
            padding=(8, 4),
        )
        style.map(
            "Field.TEntry",
            bordercolor=[("focus", _GOLD)],
            lightcolor=[("focus", _GOLD)],
            darkcolor=[("focus", _GOLD)],
        )

        style.configure(
            "Panel.TCheckbutton",
            background=_PANEL,
            foreground=_TEXT,
            font=_F_BODY,
            focuscolor=_PANEL,
            padding=(0, 2),
        )
        style.map("Panel.TCheckbutton", background=[("active", _PANEL)])
        self._install_checkbutton_indicator(style)

        style.configure("TNotebook", background=_BG, borderwidth=0, tabmargins=(0, 3, 0, 0))
        style.configure(
            "TNotebook.Tab",
            background=_TAB_IDLE,
            foreground=_MUTED,
            font=_F_BUTTON,
            padding=(16, 8),
            borderwidth=0,
            focuscolor=_TAB_IDLE,
            lightcolor=_TAB_IDLE,
            darkcolor=_TAB_IDLE,
            bordercolor=_BORDER,
        )
        style.map(
            "TNotebook.Tab",
            padding=[("selected", (16, 8, 16, 8))],
            background=[("selected", "#FFFFFF")],
            foreground=[("selected", _GOLD_DEEP)],
            lightcolor=[("selected", "#FFFFFF")],
            darkcolor=[("selected", "#FFFFFF")],
            expand=[("selected", (0, 0, 0, 0))],
        )

    def _install_checkbutton_indicator(self, style: ttk.Style) -> None:
        """Swap clam's cross indicator for bundled box images."""

        off = self._icon("check_off")
        on = self._icon("check_on")
        if off is None or on is None:
            return
        try:
            style.element_create(
                "GoldCheck.indicator", "image", off, ("selected", on), sticky=""
            )
            style.layout(
                "Panel.TCheckbutton",
                [
                    (
                        "Checkbutton.padding",
                        {
                            "sticky": "nswe",
                            "children": [
                                ("GoldCheck.indicator", {"side": "left", "sticky": ""}),
                                (
                                    "Checkbutton.focus",
                                    {
                                        "side": "left",
                                        "sticky": "w",
                                        "children": [
                                            ("Checkbutton.label", {"sticky": "nswe"})
                                        ],
                                    },
                                ),
                            ],
                        },
                    )
                ],
            )
        except tk.TclError:
            pass

    def _build(self) -> None:
        outer = tk.Frame(self, bg=_BG, padx=16, pady=12)
        outer.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)

        self.calculator_page = tk.Frame(self.notebook, bg=_BG, padx=2, pady=8)
        self.breakdown_page = tk.Frame(self.notebook, bg=_BG, padx=2, pady=8)

        calculator_icon = self._icon("calculator")
        sun_icon = self._icon("sun")
        if calculator_icon is not None:
            self.notebook.add(
                self.calculator_page,
                text="Calculator",
                image=calculator_icon,
                compound="left",
            )
        else:
            self.notebook.add(self.calculator_page, text="Calculator")
        if sun_icon is not None:
            self.notebook.add(
                self.breakdown_page,
                text="Light Radius Breakdown",
                image=sun_icon,
                compound="left",
            )
        else:
            self.notebook.add(self.breakdown_page, text="Light Radius Breakdown")

        self._build_calculator_page()
        self._build_breakdown_page()

    # ------------------------------------------------------------- primitives

    def _page_card(
        self, page: tk.Frame, heading: str, subtitle: str
    ) -> tk.Frame:
        card = tk.Frame(
            page,
            bg=_PANEL,
            highlightbackground=_BORDER,
            highlightthickness=1,
            bd=0,
        )
        card.pack(fill="both", expand=True)
        header = tk.Frame(card, bg=_PANEL)
        header.pack(fill="x", padx=20, pady=(13, 0))
        tk.Label(
            header,
            text=heading,
            font=_F_PAGE_TITLE,
            bg=_PANEL,
            fg=_TEXT,
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            header,
            text=subtitle,
            font=_F_SMALL,
            bg=_PANEL,
            fg=_MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))
        body = tk.Frame(card, bg=_PANEL)
        body.pack(fill="both", expand=True, padx=20, pady=(12, 14))
        return body

    def _section(self, parent: tk.Misc, title: str) -> tuple[tk.Frame, tk.Frame]:
        card = tk.Frame(
            parent,
            bg=_PANEL,
            highlightbackground=_BORDER,
            highlightthickness=1,
            bd=0,
        )
        tk.Label(
            card,
            text=title.upper(),
            font=_F_SECTION,
            bg=_PANEL,
            fg=_TEXT,
            anchor="w",
        ).pack(fill="x", padx=_GUTTER, pady=(13, 0))
        tk.Frame(card, bg=_RULE, height=1).pack(fill="x", padx=_GUTTER, pady=(9, 2))
        body = tk.Frame(card, bg=_PANEL)
        body.pack(fill="both", expand=True, pady=(3, 12))
        body.columnconfigure(1, weight=1)
        return card, body

    def _field_row(
        self,
        body: tk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        icon: str | None = None,
        suffix: str = "%",
        on_change: Callable[..., None] | None = None,
    ) -> ttk.Entry:
        label_pad = _GUTTER
        if icon is not None:
            photo = self._icon(icon)
            if photo is not None:
                tk.Label(body, image=photo, bg=_PANEL).grid(
                    row=row, column=0, sticky="w", padx=(_GUTTER, 0), pady=4
                )
                label_pad = 10
        tk.Label(
            body, text=label, font=_F_BODY, bg=_PANEL, fg=_TEXT, anchor="w"
        ).grid(row=row, column=1, sticky="w", padx=(label_pad, 12), pady=4)
        entry = ttk.Entry(
            body, textvariable=variable, width=9, justify="right", style="Field.TEntry"
        )
        entry.grid(row=row, column=2, sticky="e", pady=4)
        tk.Label(
            body, text=suffix, font=_F_BODY, bg=_PANEL, fg=_MUTED, width=1, anchor="w"
        ).grid(row=row, column=3, sticky="w", padx=(7, _GUTTER), pady=4)
        if on_change is not None:
            variable.trace_add("write", on_change)
        return entry

    def _check_row(
        self, body: tk.Frame, row: int, label: str, variable: tk.BooleanVar
    ) -> None:
        ttk.Checkbutton(
            body, text=label, variable=variable, style="Panel.TCheckbutton"
        ).grid(
            row=row,
            column=0,
            columnspan=4,
            sticky="w",
            padx=(_GUTTER - 2, _GUTTER),
            pady=3,
        )

    def _note_row(self, body: tk.Frame, row: int, variable: tk.StringVar) -> None:
        tk.Label(
            body,
            textvariable=variable,
            font=_F_SMALL,
            bg=_PANEL,
            fg=_MUTED,
            anchor="w",
        ).grid(row=row, column=0, columnspan=4, sticky="w", padx=_GUTTER, pady=(1, 0))

    def _result_block(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        colour: str,
        error_variable: tk.StringVar | None = None,
        *,
        rule: bool = True,
    ) -> None:
        row = tk.Frame(parent, bg=_PANEL)
        row.pack(fill="x", padx=_GUTTER, pady=(13, 2))
        tk.Label(row, text=label, font=_F_RESULT_LABEL, bg=_PANEL, fg=_MUTED).pack(
            side="left"
        )
        tk.Label(
            row, textvariable=variable, font=_F_RESULT_VALUE, bg=_PANEL, fg=colour
        ).pack(side="right")
        if error_variable is not None:
            tk.Label(
                parent,
                textvariable=error_variable,
                font=_F_SMALL,
                bg=_PANEL,
                fg=_ERROR,
                anchor="w",
            ).pack(fill="x", padx=_GUTTER)
        if rule:
            tk.Frame(parent, bg=_RULE, height=1).pack(
                fill="x", padx=_GUTTER, pady=(11, 0)
            )

    def _accent_button(
        self, parent: tk.Misc, text: str, command: Callable[[], None], icon: str | None
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=_F_BUTTON,
            bg=_GOLD,
            fg="#FFFFFF",
            activebackground=_GOLD_DEEP,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=16,
            pady=9,
            cursor="hand2",
        )
        photo = self._icon(icon) if icon else None
        if photo is not None:
            button.configure(image=photo, compound="left")
        return button

    def _outline_button(
        self, parent: tk.Misc, text: str, command: Callable[[], None], icon: str | None
    ) -> tk.Frame:
        holder = tk.Frame(parent, bg=_FIELD_BORDER)
        button = tk.Button(
            holder,
            text=text,
            command=command,
            font=_F_BUTTON,
            bg="#FFFFFF",
            fg=_TEXT,
            activebackground=_HOVER,
            activeforeground=_TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=15,
            pady=8,
            cursor="hand2",
        )
        photo = self._icon(icon) if icon else None
        if photo is not None:
            button.configure(image=photo, compound="left")
        button.pack(padx=1, pady=1)
        return holder

    # -------------------------------------------------------- calculator page

    def _build_calculator_page(self) -> None:
        body = self._page_card(
            self.calculator_page,
            "1. CALCULATOR",
            "Manual entry for the Luminary and the active permanent Mercenary. "
            "Results update as you type.",
        )
        body.columnconfigure(0, weight=1, uniform="cols")
        body.columnconfigure(1, weight=1, uniform="cols")
        body.rowconfigure(0, weight=1)

        defaults = default_manual_calculator_input()
        self.maximum_life_var = tk.StringVar(value=defaults.maximum_life)
        self.light_radius_var = tk.StringVar(value=defaults.increased_light_radius_pct)
        self.other_link_var = tk.StringVar(
            value=defaults.other_link_skill_buff_effect_pct
        )
        self.flame_link_level_var = tk.StringVar(value=defaults.flame_link_level)
        self.golden_glory_var = tk.BooleanVar(value=defaults.golden_glory_allocated)
        self.powerful_bond_var = tk.BooleanVar(value=defaults.powerful_bond_active)
        self.inspiring_bond_var = tk.BooleanVar(value=defaults.inspiring_bond_active)
        self.gear_fire_res_var = tk.StringVar(
            value=defaults.total_fire_resistance_on_gear
        )
        self.aura_fire_res_var = tk.StringVar(
            value=defaults.luminary_aura_fire_resistance
        )
        self.enmity_reduced_var = tk.StringVar(
            value=defaults.enmity_reduced_fire_resistance
        )
        self.maximum_fire_var = tk.StringVar(value=defaults.maximum_fire_resistance)
        self.enmity_equipped_var = tk.BooleanVar(value=defaults.enmity_equipped)

        left = tk.Frame(body, bg=_PANEL)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        right = tk.Frame(body, bg=_PANEL)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))

        luminary, luminary_body = self._section(left, "Luminary")
        luminary.pack(fill="x")
        self._field_row(
            luminary_body, 0, "Maximum Life", self.maximum_life_var, suffix=" "
        )
        self._field_row(
            luminary_body, 1, "Increased Light Radius Modifier", self.light_radius_var
        )
        self._field_row(
            luminary_body, 2, "Other Link Skill Buff Effect", self.other_link_var
        )
        self._field_row(
            luminary_body, 3, "Flame Link Level", self.flame_link_level_var, suffix=" "
        )
        self._check_row(luminary_body, 4, "Golden Glory Allocated", self.golden_glory_var)
        self._check_row(
            luminary_body, 5, "Powerful Bond Active (Notable)", self.powerful_bond_var
        )
        self._check_row(
            luminary_body, 6, "Inspiring Bond Active (Notable)", self.inspiring_bond_var
        )

        enmity, enmity_body = self._section(left, "Mercenary / Enmity")
        enmity.pack(fill="x", pady=(14, 0))
        self._field_row(
            enmity_body, 0, "Total Fire Resistance on Gear", self.gear_fire_res_var
        )
        self._field_row(
            enmity_body, 1, "Fire Resistance from Luminary Aura", self.aura_fire_res_var
        )
        self._field_row(
            enmity_body, 2, "Enmity Reduced Fire Resistance", self.enmity_reduced_var
        )
        self._field_row(
            enmity_body, 3, "Maximum Fire Resistance", self.maximum_fire_var
        )
        self._check_row(enmity_body, 4, "Enmity Equipped", self.enmity_equipped_var)

        self.pre_enmity_display_var = tk.StringVar(
            value=f"Pre-Enmity Fire Resistance: {_DASH}"
        )
        self.final_uncapped_display_var = tk.StringVar(
            value=f"Final Uncapped Fire Resistance: {_DASH}"
        )
        self.overcapped_display_var = tk.StringVar(
            value=f"Overcapped Fire Resistance: {_DASH}"
        )
        self.enmity_section_error_var = tk.StringVar(value="")
        tk.Frame(enmity_body, bg=_RULE, height=1).grid(
            row=5, column=0, columnspan=4, sticky="ew", padx=_GUTTER, pady=(8, 6)
        )
        self._note_row(enmity_body, 6, self.pre_enmity_display_var)
        self._note_row(enmity_body, 7, self.final_uncapped_display_var)
        self._note_row(enmity_body, 8, self.overcapped_display_var)
        tk.Label(
            enmity_body,
            textvariable=self.enmity_section_error_var,
            font=_F_SMALL,
            bg=_PANEL,
            fg=_ERROR,
            anchor="w",
        ).grid(row=9, column=0, columnspan=4, sticky="w", padx=_GUTTER, pady=(4, 0))

        results, results_body = self._section(right, "Results")
        results.pack(fill="x")

        self.net_effect_value = tk.StringVar(value=_DASH)
        self.multiplier_value = tk.StringVar(value=_DASH)
        self.flame_link_value = tk.StringVar(value=_DASH)
        self.enmity_value = tk.StringVar(value=_DASH)
        self.flame_error_var = tk.StringVar(value="")
        self.enmity_error_var = tk.StringVar(value="")

        self._result_block(
            results_body, "Effective Link Skill Buff Effect", self.net_effect_value, _TEXT
        )
        self._result_block(
            results_body, "Link Effect Multiplier", self.multiplier_value, _TEXT
        )
        self._result_block(
            results_body,
            "Flame Link Added Fire Damage",
            self.flame_link_value,
            _FLAME,
            self.flame_error_var,
        )
        self._result_block(
            results_body,
            "Enmity Fire Penetration",
            self.enmity_value,
            _ENMITY,
            self.enmity_error_var,
            rule=False,
        )
        tk.Label(
            results_body,
            text="Flame Link Added Fire Damage is the modelled damage granted to the "
            "linked Mercenary. It is not DPS.",
            font=_F_SMALL,
            bg=_PANEL,
            fg=_MUTED,
            justify="left",
            wraplength=380,
            anchor="w",
        ).pack(fill="x", padx=_GUTTER, pady=(14, 0))

        actions = tk.Frame(right, bg=_PANEL)
        actions.pack(fill="x", pady=(14, 0))
        self._outline_button(actions, "Reset", self.reset_calculator, "refresh").pack(
            side="left"
        )

        for variable in (
            self.maximum_life_var,
            self.light_radius_var,
            self.other_link_var,
            self.flame_link_level_var,
            self.gear_fire_res_var,
            self.aura_fire_res_var,
            self.enmity_reduced_var,
            self.maximum_fire_var,
        ):
            variable.trace_add("write", self._on_input_changed)
        for toggle in (
            self.golden_glory_var,
            self.powerful_bond_var,
            self.inspiring_bond_var,
            self.enmity_equipped_var,
        ):
            toggle.trace_add("write", self._on_input_changed)

    # --------------------------------------------------------- breakdown page

    def _build_breakdown_page(self) -> None:
        body = self._page_card(
            self.breakdown_page,
            "2. LIGHT RADIUS BREAKDOWN",
            "Optional detailed entry. Totals here feed the Calculator page.",
        )
        body.columnconfigure(0, weight=1, uniform="cols")
        body.columnconfigure(1, weight=1, uniform="cols")
        body.rowconfigure(0, weight=1)

        slots, slots_body = self._section(body, "Equipment and Passives")
        slots.grid(row=0, column=0, sticky="nsew", padx=(0, 9))

        self._slot_vars: dict[str, tk.StringVar] = {}
        for index, name in enumerate(FIXED_LIGHT_RADIUS_SLOTS):
            variable = tk.StringVar(value="0")
            self._slot_vars[name] = variable
            self._field_row(
                slots_body,
                index,
                name,
                variable,
                icon=SLOT_ICON_NAMES.get(name),
                on_change=self._on_breakdown_changed,
            )

        jewels, jewels_body = self._section(body, "Jewels")
        jewels.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        self._jewels_frame = tk.Frame(jewels_body, bg=_PANEL)
        self._jewels_frame.pack(fill="x")
        add_holder = tk.Frame(jewels_body, bg=_PANEL)
        add_holder.pack(fill="x", padx=_GUTTER, pady=(10, 0))
        self._add_jewel_holder = self._outline_button(
            add_holder, "Add Jewel", self.add_jewel_row, "plus"
        )
        self._add_jewel_holder.pack(anchor="w")

        total = tk.Frame(
            body,
            bg=_GOLD_SOFT,
            highlightbackground=_GOLD_EDGE,
            highlightthickness=1,
            bd=0,
        )
        total.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        sun = self._icon("sun_large")
        if sun is not None:
            tk.Label(total, image=sun, bg=_GOLD_SOFT).pack(
                side="left", padx=(_GUTTER, 12), pady=9
            )
        tk.Label(
            total,
            text="Total Increased Light Radius Modifier",
            font=_F_TOTAL_LABEL,
            bg=_GOLD_SOFT,
            fg=_TEXT,
        ).pack(side="left", pady=9)
        self.breakdown_total_var = tk.StringVar(value="0")
        tk.Label(
            total, text="%", font=_F_TOTAL_LABEL, bg=_GOLD_SOFT, fg=_GOLD
        ).pack(side="right", padx=(2, _GUTTER), pady=9)
        tk.Label(
            total,
            textvariable=self.breakdown_total_var,
            font=_F_TOTAL_VALUE,
            bg=_GOLD_SOFT,
            fg=_GOLD,
        ).pack(side="right", pady=8)

        actions = tk.Frame(body, bg=_PANEL)
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self._accent_button(
            actions, "Apply Total to Calculator", self.apply_breakdown_total, "check_light"
        ).pack(side="left")
        self._outline_button(
            actions, "Reset Breakdown", self.reset_breakdown, "refresh"
        ).pack(side="left", padx=(10, 0))

        note = tk.Frame(actions, bg=_PANEL)
        note.pack(side="right")
        info = self._icon("info")
        if info is not None:
            tk.Label(note, image=info, bg=_PANEL).pack(side="left", padx=(0, 7))
        tk.Label(
            note,
            text="You can also ignore this page and enter the total directly on the "
            "Calculator tab.",
            font=_F_SMALL,
            bg=_PANEL,
            fg=_MUTED,
            justify="left",
            wraplength=280,
        ).pack(side="left")

        self._rebuild_jewel_rows()

    def _rebuild_jewel_rows(self) -> None:
        for child in self._jewels_frame.winfo_children():
            child.destroy()
        self._jewel_vars = []
        jewel_icon = self._icon(JEWEL_ICON_NAME)
        for index, value in enumerate(self._breakdown.jewels):
            row = tk.Frame(self._jewels_frame, bg=_PANEL)
            row.pack(fill="x", pady=4)
            if jewel_icon is not None:
                tk.Label(row, image=jewel_icon, bg=_PANEL).pack(
                    side="left", padx=(_GUTTER, 10)
                )
            tk.Label(
                row, text=f"Jewel {index + 1}", font=_F_BODY, bg=_PANEL, fg=_TEXT
            ).pack(side="left")
            remove_cell = tk.Frame(row, bg=_PANEL, width=22, height=20)
            remove_cell.pack(side="right", padx=(4, _GUTTER - 8))
            remove_cell.pack_propagate(False)
            if index >= INITIAL_JEWEL_COUNT:
                tk.Button(
                    remove_cell,
                    text="\u2715",
                    command=lambda i=index: self.remove_jewel_row(i),
                    font=_F_SMALL,
                    bg=_PANEL,
                    fg=_MUTED,
                    activebackground=_HOVER,
                    activeforeground=_TEXT,
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                    cursor="hand2",
                ).pack(fill="both", expand=True)
            tk.Label(
                row, text="%", font=_F_BODY, bg=_PANEL, fg=_MUTED, width=1
            ).pack(side="right", padx=(7, 4))
            variable = tk.StringVar(value=self._format_breakdown_total(value))
            self._jewel_vars.append(variable)
            ttk.Entry(
                row,
                textvariable=variable,
                width=9,
                justify="right",
                style="Field.TEntry",
            ).pack(side="right")
            variable.trace_add("write", self._on_breakdown_changed)
        self._refresh_add_jewel_state()
        self.breakdown_total_var.set(
            self._format_breakdown_total(self._breakdown.total())
        )

    def _refresh_add_jewel_state(self) -> None:
        holder = getattr(self, "_add_jewel_holder", None)
        if holder is None:
            return
        at_cap = len(self._breakdown.jewels) >= MAXIMUM_JEWEL_ROWS
        for child in holder.winfo_children():
            if isinstance(child, tk.Button):
                child.configure(state="disabled" if at_cap else "normal")

    # ------------------------------------------------------------- behaviour

    def _on_input_changed(self, *_args: object) -> None:
        if self._updating:
            return
        self._recalculate()

    def _on_breakdown_changed(self, *_args: object) -> None:
        if self._updating:
            return
        self._sync_breakdown_model_from_vars()
        self.breakdown_total_var.set(
            self._format_breakdown_total(self._breakdown.total())
        )

    def _current_input(self) -> ManualCalculatorInput:
        return ManualCalculatorInput(
            maximum_life=self.maximum_life_var.get(),
            increased_light_radius_pct=self.light_radius_var.get(),
            other_link_skill_buff_effect_pct=self.other_link_var.get(),
            flame_link_level=self.flame_link_level_var.get(),
            golden_glory_allocated=bool(self.golden_glory_var.get()),
            powerful_bond_active=bool(self.powerful_bond_var.get()),
            inspiring_bond_active=bool(self.inspiring_bond_var.get()),
            total_fire_resistance_on_gear=self.gear_fire_res_var.get(),
            luminary_aura_fire_resistance=self.aura_fire_res_var.get(),
            enmity_reduced_fire_resistance=self.enmity_reduced_var.get(),
            maximum_fire_resistance=self.maximum_fire_var.get(),
            enmity_equipped=bool(self.enmity_equipped_var.get()),
        )

    def _recalculate(self) -> None:
        result = evaluate_manual_calculator(
            self._current_input(), level_table=self._level_table
        )
        if result.net_link_skill_buff_effect_pct is None:
            self.net_effect_value.set(_DASH)
        else:
            self.net_effect_value.set(f"{result.net_link_skill_buff_effect_pct}%")
        if result.link_effect_multiplier is None:
            self.multiplier_value.set(_DASH)
        else:
            self.multiplier_value.set(f"{result.link_effect_multiplier}x")
        if result.flame_link_min is None or result.flame_link_max is None:
            self.flame_link_value.set(_DASH)
        else:
            self.flame_link_value.set(
                f"{result.flame_link_min}-{result.flame_link_max}"
            )
        self.flame_error_var.set(result.flame_link_error or "")

        self.pre_enmity_display_var.set(
            "Pre-Enmity Fire Resistance: "
            + (
                _DASH
                if result.pre_enmity_fire_resistance is None
                else f"{result.pre_enmity_fire_resistance}%"
            )
        )
        self.final_uncapped_display_var.set(
            "Final Uncapped Fire Resistance: "
            + (
                _DASH
                if result.final_uncapped_fire_resistance is None
                else f"{result.final_uncapped_fire_resistance}%"
            )
        )
        self.overcapped_display_var.set(
            "Overcapped Fire Resistance: "
            + (
                _DASH
                if result.overcapped_fire_resistance is None
                else f"{result.overcapped_fire_resistance}%"
            )
        )

        if not self.enmity_equipped_var.get():
            self.enmity_value.set(_DASH)
            self.enmity_error_var.set("")
            self.enmity_section_error_var.set(result.enmity_error or "")
        elif result.enmity_penetration is None:
            self.enmity_value.set(_DASH)
            self.enmity_error_var.set(result.enmity_error or "")
            self.enmity_section_error_var.set(result.enmity_error or "")
        else:
            self.enmity_value.set(f"{result.enmity_penetration}%")
            self.enmity_error_var.set(result.enmity_error or "")
            self.enmity_section_error_var.set("")

    def reset_calculator(self) -> None:
        defaults = default_manual_calculator_input()
        self._updating = True
        try:
            self.maximum_life_var.set(defaults.maximum_life)
            self.light_radius_var.set(defaults.increased_light_radius_pct)
            self.other_link_var.set(defaults.other_link_skill_buff_effect_pct)
            self.flame_link_level_var.set(defaults.flame_link_level)
            self.golden_glory_var.set(defaults.golden_glory_allocated)
            self.powerful_bond_var.set(defaults.powerful_bond_active)
            self.inspiring_bond_var.set(defaults.inspiring_bond_active)
            self.gear_fire_res_var.set(defaults.total_fire_resistance_on_gear)
            self.aura_fire_res_var.set(defaults.luminary_aura_fire_resistance)
            self.enmity_reduced_var.set(defaults.enmity_reduced_fire_resistance)
            self.maximum_fire_var.set(defaults.maximum_fire_resistance)
            self.enmity_equipped_var.set(defaults.enmity_equipped)
        finally:
            self._updating = False
        self._recalculate()

    def _format_breakdown_total(self, total: Decimal) -> str:
        if total == total.to_integral_value():
            return str(int(total))
        return format(total.normalize(), "f")

    def _sync_breakdown_model_from_vars(self) -> None:
        for name, variable in self._slot_vars.items():
            self._breakdown.slots[name] = self._parse_breakdown_number(variable.get())
        values: list[Decimal] = [
            self._parse_breakdown_number(variable.get())
            for variable in self._jewel_vars
        ]
        while len(values) < INITIAL_JEWEL_COUNT:
            values.append(Decimal(0))
        self._breakdown.jewels = values

    def _parse_breakdown_number(self, text: str) -> Decimal:
        stripped = text.strip()
        if not stripped or stripped in {"+", "-"}:
            return Decimal(0)
        try:
            return Decimal(stripped)
        except Exception:
            return Decimal(0)

    def add_jewel_row(self) -> None:
        self._sync_breakdown_model_from_vars()
        if len(self._breakdown.jewels) >= MAXIMUM_JEWEL_ROWS:
            return
        self._breakdown.add_jewel()
        self._rebuild_jewel_rows()

    def remove_jewel_row(self, index: int) -> None:
        self._sync_breakdown_model_from_vars()
        if self._breakdown.can_remove_jewel(index):
            self._breakdown.remove_jewel(index)
            self._rebuild_jewel_rows()

    def apply_breakdown_total(self) -> None:
        self._sync_breakdown_model_from_vars()
        total = self._breakdown.total()
        self.light_radius_var.set(self._format_breakdown_total(total))
        self.notebook.select(self.calculator_page)

    def reset_breakdown(self) -> None:
        self._breakdown.reset()
        self._updating = True
        try:
            for variable in self._slot_vars.values():
                variable.set("0")
        finally:
            self._updating = False
        self._rebuild_jewel_rows()

    def top_level_page_titles(self) -> tuple[str, ...]:
        return tuple(self.notebook.tab(index, "text") for index in self.notebook.tabs())
