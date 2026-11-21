"""
Voice-Enhanced Linux: Balanced Midnight Indigo & Cyan UI (Flet 1.1+ & VM optimized)
Rich, lively depth with a cohesive 2-tone Indigo + Cyan palette—neither cluttered nor dull.
"""
from __future__ import annotations

import math
import os
import random
from pathlib import Path
import queue
import threading
import time
from typing import Callable, List, Optional, Tuple

import flet as ft

try:
    import psutil
except ImportError:
    psutil = None

from gui.events import (
    CONFIRM_TIMEOUT_SECONDS,
    EXECUTION_STATUSES,
    TERMINAL_EXECUTION,
    Confirm,
    Emit,
    Event,
)
from gui.standins import StandInPipeline
from tts import speaker

# Balanced Midnight Indigo & Cyan Palette (Lively yet eye-resting)
BG_TOP = "#0D1426"
BG_MID = "#131C33"
BG_BOT = "#11172E"

HEADER_BG = "#151F38"
CARD_BG = "#18233E"
SIDEBAR_BG = "#141D35"
ROW_BG = "#1F2C4C"
BADGE_CYAN_BG = "#172E4D"
BADGE_INDIGO_BG = "#21254D"

BORDER_SUBTLE = "#283657"
BORDER_ACCENT = "#3B5998"

ACCENT_CYAN = "#38BDF8"
ACCENT_INDIGO = "#818CF8"
ACCENT_BLUE = "#3B82F6"

SUCCESS_FG = "#34D399"
SUCCESS_BG = "#13312E"
DANGER_FG = "#F87171"
DANGER_BG = "#331B24"
WARN_FG = "#FBBF24"
WARN_BG = "#332918"

TEXT_MAIN = "#F8FAFC"
TEXT_MUTED = "#9AA7BD"

PIPELINE_STEPS = [
    ("1. Audio", ft.Icons.MIC_NONE_ROUNDED),
    ("2. Whisper STT", ft.Icons.SUBTITLES_ROUNDED),
    ("3. NLP Intent", ft.Icons.PSYCHOLOGY_ROUNDED),
    ("4. Safety Gate", ft.Icons.SHIELD_ROUNDED),
    ("5. OS Exec", ft.Icons.TERMINAL_ROUNDED),
]

PIPELINE_STEPS_AR = [
    "١. التقاط الصوت",
    "٢. تحويل النص",
    "٣. فهم الأمر",
    "٤. بوابة الأمان",
    "٥. تنفيذ النظام",
]

QUICK_COMMANDS = {
    "en": [
        ("Open calculator", ft.Icons.CALCULATE_ROUNDED),
        ("Create file demo", ft.Icons.NOTE_ADD_ROUNDED),
        ("List files", ft.Icons.FOLDER_OPEN_ROUNDED),
        ("Close calculator", ft.Icons.CLOSE_ROUNDED),
    ],
    "ar": [
        ("افتح الآلة الحاسبة", ft.Icons.CALCULATE_ROUNDED),
        ("أنشئ ملف جديد", ft.Icons.NOTE_ADD_ROUNDED),
        ("اعرض الملفات", ft.Icons.FOLDER_OPEN_ROUNDED),
        ("اغلق الآلة الحاسبة", ft.Icons.CLOSE_ROUNDED),
    ],
}

STATE_THEMES = {
    "ready": {
        "label": "Ready",
        "fg": SUCCESS_FG,
        "pill_bg": SUCCESS_BG,
        "border": "#23534A",
        "mic_grad": ["#2563EB", "#4F46E5"],
        "halo_inner": "#2E3B82F6",
        "halo_outer": "#176366F1",
    },
    "listening": {
        "label": "Listening...",
        "fg": DANGER_FG,
        "pill_bg": DANGER_BG,
        "border": "#6B2B38",
        "mic_grad": ["#DC2626", "#E11D48"],
        "halo_inner": "#38EF4444",
        "halo_outer": "#1CEF4444",
    },
    "processing": {
        "label": "Processing...",
        "fg": WARN_FG,
        "pill_bg": WARN_BG,
        "border": "#6B5224",
        "mic_grad": ["#D97706", "#EA580C"],
        "halo_inner": "#38F59E0B",
        "halo_outer": "#1CF59E0B",
    },
    "speaking": {
        "label": "Speaking...",
        "fg": ACCENT_CYAN,
        "pill_bg": BADGE_CYAN_BG,
        "border": "#2B5B8A",
        "mic_grad": ["#0284C7", "#3B82F6"],
        "halo_inner": "#3838BDF8",
        "halo_outer": "#1C818CF8",
    },
    "error": {
        "label": "Error",
        "fg": DANGER_FG,
        "pill_bg": DANGER_BG,
        "border": "#6B2B38",
        "mic_grad": ["#DC2626", "#B91C1C"],
        "halo_inner": "#38EF4444",
        "halo_outer": "#1CEF4444",
    },
}

STATUS_BADGES = {
    "awaiting_confirmation": ("Awaiting Confirmation", WARN_FG, WARN_BG),
    "running": ("Running...", ACCENT_CYAN, BADGE_CYAN_BG),
    "completed": ("Completed", SUCCESS_FG, SUCCESS_BG),
    "rejected": ("Rejected", DANGER_FG, DANGER_BG),
    "failed": ("Failed", DANGER_FG, DANGER_BG),
    "cancelled": ("Cancelled", TEXT_MUTED, ROW_BG),
}


def _read_system_metrics(prev_cpu: Optional[Tuple[int, int]]) -> Tuple[float, float, str, Optional[Tuple[int, int]]]:
    if psutil is not None:
        cpu_pct = float(psutil.cpu_percent(interval=None))
        vm = psutil.virtual_memory()
        used_gb = (vm.total - vm.available) / (1024 ** 3)
        total_gb = vm.total / (1024 ** 3)
        return cpu_pct, float(vm.percent), f"{used_gb:.1f} / {total_gb:.1f} GB", prev_cpu

    cpu_pct = 0.0
    next_cpu = prev_cpu
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            parts = [int(x) for x in f.readline().split()[1:8]]
        idle = parts[3] + parts[4]
        total = sum(parts)
        if prev_cpu is not None:
            d_total = total - prev_cpu[0]
            d_idle = idle - prev_cpu[1]
            if d_total > 0:
                cpu_pct = max(0.0, min(100.0, 100.0 * (1.0 - d_idle / d_total)))
        next_cpu = (total, idle)
    except Exception:
        pass

    ram_pct = 0.0
    ram_str = "- / - GB"
    try:
        info = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k.strip()] = int(v.strip().split()[0])
        total_kb = info.get("MemTotal", 1)
        avail_kb = info.get("MemAvailable", info.get("MemFree", 0))
        used_kb = max(0, total_kb - avail_kb)
        ram_pct = 100.0 * used_kb / total_kb
        ram_str = f"{used_kb / (1024 ** 2):.1f} / {total_kb / (1024 ** 2):.1f} GB"
    except Exception:
        pass

    return cpu_pct, ram_pct, ram_str, next_cpu


def _metric_color(pct: float, default_color: str) -> str:
    if pct >= 85.0:
        return DANGER_FG
    if pct >= 72.0:
        return WARN_FG
    return default_color


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 ** 2):.1f} MB"


def _icon_badge(icon_name, is_indigo: bool = False) -> ft.Container:
    fg = ACCENT_INDIGO if is_indigo else ACCENT_CYAN
    bg = BADGE_INDIGO_BG if is_indigo else BADGE_CYAN_BG
    bd = "#373D75" if is_indigo else "#264B78"
    return ft.Container(
        content=ft.Icon(icon_name, size=14, color=fg),
        width=27,
        height=27,
        border_radius=8,
        bgcolor=bg,
        border=ft.Border.all(1, bd),
        alignment=ft.Alignment.CENTER,
    )


class ModernVoiceApp:
    def __init__(
        self,
        page: ft.Page,
        pipeline: Optional[Callable[[Emit, str, Confirm], None]] = None,
        text_pipeline: Optional[Callable[[Emit, str, str, Confirm], None]] = None,
        speak_fn: Callable[[str, str], bool] = speaker.speak,
        workspace: str = "~/VoiceLinuxWorkspace",
        model_name: str = "faster-whisper (small)",
    ):
        self.page = page
        self.pipeline = pipeline or StandInPipeline()
        self.text_pipeline = text_pipeline
        self._speak = speak_fn
        self.workspace = workspace
        self.model_name = model_name

        self._tts_queue: "queue.Queue[object]" = queue.Queue()
        self._ui_lock = threading.Lock()
        self._busy = False
        self._closing = False
        self._voice_on = True
        self._lang = "en"
        self._current = {"command": "", "intent": ""}
        self._prev_cpu: Optional[Tuple[int, int]] = None

        self._ui_state = "ready"
        self._eq_bars: List[ft.Container] = []
        self._step_boxes: List[ft.Container] = []
        self._step_icons: List[ft.Icon] = []
        self._step_labels: List[ft.Text] = []
        self._step_arrows: List[ft.Icon] = []

        self._configure_page()
        self._build_ui()
        self._rebuild_quick_chips()
        self._reset_stepper()
        self._set_state("ready")
        self._update_metrics_once()
        self._refresh_workspace_files()
        self.page.update()

        threading.Thread(target=self._tts_loop, daemon=True).start()
        threading.Thread(target=self._metrics_loop, daemon=True).start()
        threading.Thread(target=self._visualizer_loop, daemon=True).start()

    def _refresh(self) -> None:
        async def _flush():
            self.page.update()

        try:
            self.page.run_task(_flush)
        except Exception:
            self.page.update()

    def _configure_page(self) -> None:
        self.page.title = "Voice-Enhanced Linux"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = BG_TOP
        self.page.padding = 0
        self.page.window.width = 1160
        self.page.window.height = 820
        self.page.window.min_width = 960
        self.page.window.min_height = 680
        self.page.on_disconnect = lambda _: self.close()

    def _card(
        self,
        content: ft.Control,
        padding: int = 13,
        radius: int = 14,
        border_color: str = BORDER_SUBTLE,
        expand: bool = False,
        width: Optional[float] = None,
        height: Optional[float] = None,
        bg: str = CARD_BG,
    ) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=bg,
            border=ft.Border.all(1, border_color),
            border_radius=radius,
            padding=padding,
            expand=expand,
            width=width,
            height=height,
        )

    def _build_stepper(self) -> ft.Container:
        row_items: List[ft.Control] = []
        for idx, (label, icon_name) in enumerate(PIPELINE_STEPS):
            ic = ft.Icon(icon_name, size=14, color=TEXT_MUTED)
            tx = ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED)
            box = ft.Container(
                content=ft.Row([ic, tx], spacing=6, alignment=ft.MainAxisAlignment.CENTER, tight=True),
                bgcolor=SIDEBAR_BG,
                border=ft.Border.all(1, BORDER_SUBTLE),
                border_radius=9,
                padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                expand=True,
            )
            self._step_boxes.append(box)
            self._step_icons.append(ic)
            self._step_labels.append(tx)
            row_items.append(box)

            if idx < len(PIPELINE_STEPS) - 1:
                arr = ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, size=15, color="#475569")
                self._step_arrows.append(arr)
                row_items.append(arr)

        self.stepper_row = ft.Row(row_items, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        return ft.Container(
            content=self.stepper_row,
            bgcolor=CARD_BG,
            border=ft.Border.all(1, BORDER_SUBTLE),
            border_radius=12,
            padding=7,
        )

    def _set_step_style(self, idx: int, status: str) -> None:
        styles = {
            "idle": (SIDEBAR_BG, BORDER_SUBTLE, TEXT_MUTED, TEXT_MUTED),
            "active": (BADGE_CYAN_BG, ACCENT_CYAN, ACCENT_CYAN, TEXT_MAIN),
            "done": (BADGE_INDIGO_BG, "#4F46E5", ACCENT_INDIGO, TEXT_MAIN),
            "warn": (WARN_BG, "#6B5224", WARN_FG, WARN_FG),
            "fail": (DANGER_BG, "#6B2B38", DANGER_FG, DANGER_FG),
        }
        bg, border, ic_col, tx_col = styles.get(status, styles["idle"])
        box = self._step_boxes[idx]
        box.bgcolor = bg
        box.border = ft.Border.all(1, border)
        self._step_icons[idx].color = ic_col
        self._step_labels[idx].color = tx_col
        if idx > 0 and idx - 1 < len(self._step_arrows):
            self._step_arrows[idx - 1].color = ic_col if status != "idle" else "#475569"

    def _reset_stepper(self) -> None:
        for i in range(len(PIPELINE_STEPS)):
            self._set_step_style(i, "idle")
        for arr in self._step_arrows:
            arr.color = "#475569"

    def _build_ui(self) -> None:
        # --------------------------------------------------------- Top Header
        self.state_dot = ft.Container(width=9, height=9, border_radius=5, bgcolor=SUCCESS_FG)
        self.state_text = ft.Text("Ready", size=12, weight=ft.FontWeight.W_600, color=SUCCESS_FG)
        self.state_pill = ft.Container(
            content=ft.Row([self.state_dot, self.state_text], spacing=7, tight=True),
            padding=ft.Padding.symmetric(horizontal=13, vertical=6),
            border_radius=20,
            bgcolor=SUCCESS_BG,
            border=ft.Border.all(1, "#23534A"),
        )

        self.lang_switch = ft.SegmentedButton(
            selected=["en"],
            allow_multiple_selection=False,
            segments=[
                ft.Segment(value="en", label=ft.Text("EN")),
                ft.Segment(value="ar", label=ft.Text("عربي")),
            ],
            on_change=self._on_lang_change,
        )

        self.voice_switch = ft.Switch(
            label="Voice Reply",
            value=True,
            active_color=ACCENT_CYAN,
            on_change=self._on_voice_toggle,
        )

        header_bar = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.GRAPHIC_EQ_ROUNDED, color=TEXT_MAIN, size=21),
                                width=38,
                                height=38,
                                border_radius=10,
                                gradient=ft.LinearGradient(
                                    begin=ft.Alignment.TOP_LEFT,
                                    end=ft.Alignment.BOTTOM_RIGHT,
                                    colors=["#2563EB", "#6366F1"],
                                ),
                                border=ft.Border.all(1, "#60A5FA"),
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text("Voice-Enhanced Linux", size=17, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                            ft.Container(
                                                content=ft.Text("UBUNTU", size=9, weight=ft.FontWeight.BOLD, color=ACCENT_INDIGO),
                                                padding=ft.Padding.symmetric(horizontal=7, vertical=2),
                                                border_radius=5,
                                                bgcolor=BADGE_INDIGO_BG,
                                                border=ft.Border.all(1, "#373D75"),
                                            ),
                                        ],
                                        spacing=8,
                                    ),
                                    ft.Text("Bilingual Voice Command & Execution Control Center", size=11, color=TEXT_MUTED),
                                ],
                                spacing=1,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        [self.lang_switch, self.voice_switch, self.state_pill],
                        spacing=14,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=HEADER_BG,
            border=ft.Border.all(1, BORDER_SUBTLE),
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        )

        # --------------------------------------------------------- Left Column
        stepper_bar = self._build_stepper()

        # Layered Voice Halo + Gradient Mic Button
        self.mic_icon = ft.Icon(ft.Icons.MIC_ROUNDED, color=TEXT_MAIN, size=30)
        self.mic_btn = ft.Container(
            content=self.mic_icon,
            width=62,
            height=62,
            border_radius=31,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#2563EB", "#4F46E5"],
            ),
            border=ft.Border.all(1.5, "#93C5FD"),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=self._on_listen_click,
        )
        self.mic_halo_inner = ft.Container(
            content=self.mic_btn,
            width=76,
            height=76,
            border_radius=38,
            bgcolor="#2E3B82F6",
            alignment=ft.Alignment.CENTER,
        )
        self.mic_halo_outer = ft.Container(
            content=self.mic_halo_inner,
            width=90,
            height=90,
            border_radius=45,
            bgcolor="#176366F1",
            alignment=ft.Alignment.CENTER,
        )

        self.command_text = ft.Text(
            "Tap the microphone and speak a command...",
            size=20,
            weight=ft.FontWeight.W_600,
            color=TEXT_MUTED,
        )
        self.detected_lang_badge = ft.Container(
            content=ft.Text("ENGLISH", size=10, weight=ft.FontWeight.BOLD, color=ACCENT_CYAN),
            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
            border_radius=6,
            bgcolor=BADGE_CYAN_BG,
            border=ft.Border.all(1, "#264B78"),
            visible=False,
        )

        self.chips_label = ft.Text("QUICK COMMANDS:", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED)
        self.chips_row = ft.Row(spacing=7, wrap=True)

        self.hero_cmd_header = ft.Row(
            [
                ft.Text("RECOGNIZED COMMAND", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                self.detected_lang_badge,
            ],
            spacing=8,
        )
        self.hero_cmd_col = ft.Column(
            [
                self.hero_cmd_header,
                self.command_text,
            ],
            spacing=5,
            expand=True,
        )
        idle_heights = [10, 16, 24, 14, 28, 20, 12, 26, 18, 30, 15, 22, 12, 25, 16, 10]
        bar_palette = [ACCENT_CYAN, "#60A5FA", ACCENT_INDIGO, "#A78BFA"]
        for i, h in enumerate(idle_heights):
            bar = ft.Container(
                width=4,
                height=h,
                border_radius=3,
                bgcolor=bar_palette[i % len(bar_palette)],
            )
            self._eq_bars.append(bar)

        self.visualizer_box = ft.Container(
            content=ft.Row(
                self._eq_bars,
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=48,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            border_radius=12,
            bgcolor="#121B33",
            border=ft.Border.all(1, BORDER_SUBTLE),
        )

        self.hero_main_row = ft.Row(
            [
                self.mic_halo_outer,
                self.hero_cmd_col,
                self.visualizer_box,
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.chips_container_row = ft.Row(
            [self.chips_label, self.chips_row],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.hero_card = ft.Container(
            content=ft.Column(
                [
                    self.hero_main_row,
                    ft.Divider(height=1, color=BORDER_SUBTLE),
                    self.chips_container_row,
                ],
                spacing=10,
            ),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#182747", "#1F2247"],
            ),
            border=ft.Border.all(1, BORDER_ACCENT),
            border_radius=15,
            padding=14,
        )

        # Intent & Execution Cards (Cohesive Indigo & Cyan Icon Badges)
        self.intent_text = ft.Text("-", size=15, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)
        self.intent_sub = ft.Text("Waiting for input", size=11, color=TEXT_MUTED)
        self.understanding_card = self._card(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            _icon_badge(ft.Icons.VERIFIED_USER_ROUNDED, is_indigo=True),
                            ft.Text("INTENT & VALIDATION", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                        ],
                        spacing=8,
                    ),
                    self.intent_text,
                    self.intent_sub,
                ],
                spacing=5,
            ),
            padding=12,
            radius=13,
            expand=True,
        )

        self.exec_status_text = ft.Text("Idle", size=15, weight=ft.FontWeight.BOLD, color=TEXT_MUTED)
        self.exec_sub = ft.Text("No active operation", size=11, color=TEXT_MUTED)
        self.execution_card = self._card(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            _icon_badge(ft.Icons.BOLT_ROUNDED, is_indigo=False),
                            ft.Text("EXECUTION STATUS", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                        ],
                        spacing=8,
                    ),
                    self.exec_status_text,
                    self.exec_sub,
                ],
                spacing=5,
            ),
            padding=12,
            radius=13,
            expand=True,
        )

        mid_row = ft.Row([self.understanding_card, self.execution_card], spacing=10)

        # Result Output Card
        self.result_text = ft.Text(
            "System output will appear here.",
            size=14,
            color=TEXT_MAIN,
            selectable=True,
        )
        result_card = self._card(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            _icon_badge(ft.Icons.ARTICLE_ROUNDED, is_indigo=False),
                            ft.Text("RESULT OUTPUT", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                        ],
                        spacing=8,
                    ),
                    ft.Container(
                        content=ft.Column([self.result_text], scroll=ft.ScrollMode.AUTO),
                        height=38,
                    ),
                ],
                spacing=6,
            ),
            padding=12,
            radius=13,
            width=float("inf"),
        )

        # Session History Card
        clear_btn = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.DELETE_SWEEP_ROUNDED, size=13, color=TEXT_MUTED),
                    ft.Text("Clear", size=11, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
                ],
                spacing=4,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=9, vertical=3),
            border_radius=7,
            bgcolor=ROW_BG,
            border=ft.Border.all(1, BORDER_SUBTLE),
            ink=True,
            on_click=self._clear_history,
        )

        history_header = ft.Container(
            content=ft.Row(
                [
                    ft.Text("TIME", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, width=72),
                    ft.Text("COMMAND", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, expand=2),
                    ft.Text("INTENT", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, expand=1),
                    ft.Text("STATUS", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, width=110, text_align=ft.TextAlign.RIGHT),
                ],
            ),
            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        )

        self.history_empty = ft.Text("No commands executed yet in this session.", size=12, color=TEXT_MUTED)
        self.history_list = ft.ListView(expand=True, spacing=5)

        history_card = self._card(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    _icon_badge(ft.Icons.HISTORY_ROUNDED, is_indigo=True),
                                    ft.Text("SESSION HISTORY", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                                ],
                                spacing=8,
                            ),
                            clear_btn,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    history_header,
                    ft.Divider(height=1, color=BORDER_SUBTLE),
                    self.history_empty,
                    self.history_list,
                ],
                spacing=4,
                expand=True,
            ),
            padding=12,
            radius=13,
            width=float("inf"),
            expand=True,
        )

        left_column = ft.Column(
            [stepper_bar, self.hero_card, mid_row, result_card, history_card],
            spacing=8,
            expand=True,
        )

        # --------------------------------------------------------- Right Column (Live OS & Workspace Sidebar)
        cores = os.cpu_count() or 1
        self.cpu_pct_text = ft.Text("0.0%", size=15, weight=ft.FontWeight.BOLD, color=ACCENT_CYAN)
        self.cpu_bar = ft.ProgressBar(
            value=0.0,
            color=ACCENT_CYAN,
            bgcolor=ROW_BG,
            height=5,
            border_radius=4,
        )
        self.ram_pct_text = ft.Text("0.0%", size=15, weight=ft.FontWeight.BOLD, color=ACCENT_INDIGO)
        self.ram_detail_text = ft.Text("- / - GB", size=11, color=TEXT_MUTED)
        self.ram_bar = ft.ProgressBar(
            value=0.0,
            color=ACCENT_INDIGO,
            bgcolor=ROW_BG,
            height=5,
            border_radius=4,
        )

        telemetry_card = self._card(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            _icon_badge(ft.Icons.MONITOR_HEART_ROUNDED, is_indigo=False),
                            ft.Text("LIVE UBUNTU TELEMETRY", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(height=1, color=BORDER_SUBTLE),
                    ft.Row(
                        [
                            ft.Text(f"CPU Load ({cores} vCPU)", size=12, color=TEXT_MAIN),
                            self.cpu_pct_text,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.cpu_bar,
                    ft.Container(height=4),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text("Memory (RAM)", size=12, color=TEXT_MAIN),
                                    self.ram_detail_text,
                                ],
                                spacing=0,
                            ),
                            self.ram_pct_text,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.ram_bar,
                ],
                spacing=6,
            ),
            padding=13,
            radius=13,
            bg=SIDEBAR_BG,
        )

        # Live Safe Workspace Explorer
        refresh_ws_btn = ft.Container(
            content=ft.Icon(ft.Icons.REFRESH_ROUNDED, size=14, color=ACCENT_CYAN),
            padding=5,
            border_radius=7,
            bgcolor=ROW_BG,
            border=ft.Border.all(1, BORDER_SUBTLE),
            ink=True,
            on_click=lambda _: self._manual_refresh_ws(),
        )

        self.ws_count_text = ft.Text("0 items", size=11, color=TEXT_MUTED)
        self.ws_empty_text = ft.Text("Workspace is empty.\nTry 'Create file demo'.", size=12, color=TEXT_MUTED)
        self.ws_files_list = ft.ListView(expand=True, spacing=5)

        workspace_card = self._card(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    _icon_badge(ft.Icons.FOLDER_SPECIAL_ROUNDED, is_indigo=True),
                                    ft.Text("SAFE WORKSPACE", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                                ],
                                spacing=8,
                            ),
                            ft.Row([self.ws_count_text, refresh_ws_btn], spacing=8),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        content=ft.Text(self.workspace, size=10, color=ACCENT_CYAN, font_family="monospace", selectable=True),
                        bgcolor="#0E1526",
                        border=ft.Border.all(1, BORDER_SUBTLE),
                        border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                        width=float("inf"),
                    ),
                    self.ws_empty_text,
                    self.ws_files_list,
                ],
                spacing=7,
                expand=True,
            ),
            padding=13,
            radius=13,
            expand=True,
            bg=SIDEBAR_BG,
        )

        right_column = ft.Container(
            content=ft.Column(
                [telemetry_card, workspace_card],
                spacing=8,
                expand=True,
            ),
            width=330,
        )

        body_split = ft.Row(
            [left_column, right_column],
            spacing=10,
            expand=True,
        )

        voice_status = "espeak-ng ready" if speaker.is_available() else "espeak-ng missing"
        footer = ft.Container(
            content=ft.Row(
                [
                    ft.Text(f"Sandbox Root: {self.workspace}", size=11, color=TEXT_MUTED),
                    ft.Text(f"ASR Engine: {self.model_name}  •  TTS: {voice_status}", size=11, color=TEXT_MUTED),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding.symmetric(horizontal=4),
        )

        # Confirmation Overlay Modal
        self.confirm_prompt_txt = ft.Text("", size=16, color=TEXT_MAIN)
        self.confirm_timer_txt = ft.Text("", size=12, color=DANGER_FG)
        self.confirm_yes_btn = ft.Container(
            content=ft.Text("Confirm", weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            bgcolor="#DC2626",
            border=ft.Border.all(1, DANGER_FG),
            padding=ft.Padding.symmetric(horizontal=22, vertical=10),
            border_radius=10,
            ink=True,
        )
        self.confirm_no_btn = ft.Container(
            content=ft.Text("Cancel", weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            bgcolor=ROW_BG,
            border=ft.Border.all(1, BORDER_ACCENT),
            padding=ft.Padding.symmetric(horizontal=22, vertical=10),
            border_radius=10,
            ink=True,
        )

        confirm_box = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            _icon_badge(ft.Icons.WARNING_AMBER_ROUNDED, is_indigo=False),
                            ft.Text("Confirmation Required", size=18, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ],
                        spacing=10,
                    ),
                    self.confirm_prompt_txt,
                    self.confirm_timer_txt,
                    ft.Row([self.confirm_no_btn, self.confirm_yes_btn], alignment=ft.MainAxisAlignment.END, spacing=12),
                ],
                tight=True,
                spacing=14,
            ),
            bgcolor=CARD_BG,
            border=ft.Border.all(1, "#6B5224"),
            border_radius=14,
            padding=24,
            width=450,
        )

        self.confirm_overlay = ft.Container(
            content=confirm_box,
            alignment=ft.Alignment.CENTER,
            bgcolor="#AA080D1A",
            expand=True,
            visible=False,
        )

        ambient_bg = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[BG_TOP, BG_MID, BG_BOT],
            ),
        )

        main_layout = ft.Container(
            content=ft.Column(
                [header_bar, body_split, footer],
                spacing=8,
                expand=True,
            ),
            padding=12,
            expand=True,
        )

        self.page.add(
            ft.Stack(
                [ambient_bg, main_layout, self.confirm_overlay],
                expand=True,
            )
        )

    # --------------------------------------------------------- Workspace Explorer
    def _refresh_workspace_files(self) -> None:
        ws_path = Path(os.path.expanduser(self.workspace))
        rows: List[ft.Control] = []
        try:
            if ws_path.exists() and ws_path.is_dir():
                entries = sorted(
                    ws_path.iterdir(),
                    key=lambda p: (not p.is_dir(), p.name.lower()),
                )
                for entry in entries:
                    if entry.name.startswith("."):
                        continue
                    is_dir = entry.is_dir()
                    icon = ft.Icons.FOLDER_ROUNDED if is_dir else ft.Icons.DESCRIPTION_ROUNDED
                    meta = "Folder" if is_dir else _format_size(entry.stat().st_size)
                    rows.append(
                        ft.Container(
                            content=ft.Row(
                                [
                                    _icon_badge(icon, is_indigo=is_dir),
                                    ft.Text(entry.name, size=12, color=TEXT_MAIN, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(meta, size=10, color=TEXT_MUTED),
                                ],
                                spacing=8,
                            ),
                            bgcolor=ROW_BG,
                            border=ft.Border.all(1, BORDER_SUBTLE),
                            border_radius=8,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=5),
                        )
                    )
        except Exception:
            pass

        self.ws_files_list.controls = rows
        self.ws_count_text.value = f"{len(rows)} items"
        self.ws_empty_text.visible = len(rows) == 0

    def _manual_refresh_ws(self) -> None:
        with self._ui_lock:
            self._refresh_workspace_files()
            self._refresh()

    # --------------------------------------------------------- Quick Chips
    def _rebuild_quick_chips(self) -> None:
        cmds = QUICK_COMMANDS.get(self._lang, QUICK_COMMANDS["en"])
        self.chips_label.value = "أوامر سريعة:" if self._lang == "ar" else "QUICK COMMANDS:"
        chips = []
        for cmd_text, icon_name in cmds:
            chip = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon_name, size=13, color=ACCENT_CYAN),
                        ft.Text(cmd_text, size=11, weight=ft.FontWeight.W_500, color=TEXT_MAIN),
                    ],
                    spacing=5,
                    tight=True,
                ),
                bgcolor=ROW_BG,
                border=ft.Border.all(1, BORDER_ACCENT),
                border_radius=18,
                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                ink=True,
                on_click=lambda _, c=cmd_text: self._on_chip_click(c),
            )
            chips.append(chip)
        self.chips_row.controls = chips

    def _on_chip_click(self, cmd_text: str) -> None:
        if self._busy or self._closing:
            return
        with self._ui_lock:
            self._busy = True
            self._current = {"command": "", "intent": ""}
            self._reset_stepper()
            self._set_step_style(0, "done")
            self._set_step_style(1, "done")
            self._set_step_style(2, "active")
            self._set_state("processing")
            self.detected_lang_badge.visible = False
            self.intent_text.value = "-"
            self.intent_text.color = TEXT_MAIN
            self.intent_sub.value = "Analyzing..."
            self.understanding_card.border = ft.Border.all(1, BORDER_SUBTLE)
            self.exec_status_text.value = "Waiting"
            self.exec_status_text.color = TEXT_MUTED
            self.exec_sub.value = ""
            self.execution_card.border = ft.Border.all(1, BORDER_SUBTLE)
            self.result_text.value = ""
            self._refresh()

        threading.Thread(
            target=self._run_chip_pipeline,
            args=(cmd_text, self._lang),
            daemon=True,
        ).start()

    def _run_chip_pipeline(self, cmd_text: str, language: str) -> None:
        try:
            if self.text_pipeline is not None:
                self.text_pipeline(self.emit, cmd_text, language, self.confirm)
            else:
                self.emit(Event("command", language, cmd_text))
                self.pipeline(self.emit, language, self.confirm)
        except Exception as exc:
            self.emit(Event("error", "failed", f"Unexpected error: {exc}"))
        finally:
            self._tts_queue.join()
            self._busy = False
            self.emit(Event("listening", "ready"))

    # --------------------------------------------------------- Live Telemetry
    def _update_metrics_once(self) -> None:
        cpu_pct, ram_pct, ram_str, self._prev_cpu = _read_system_metrics(self._prev_cpu)
        cpu_col = _metric_color(cpu_pct, ACCENT_CYAN)
        ram_col = _metric_color(ram_pct, ACCENT_INDIGO)

        self.cpu_pct_text.value = f"{cpu_pct:.1f}%"
        self.cpu_pct_text.color = cpu_col
        self.cpu_bar.value = min(1.0, max(0.0, cpu_pct / 100.0))
        self.cpu_bar.color = cpu_col

        self.ram_pct_text.value = f"{ram_pct:.1f}%"
        self.ram_pct_text.color = ram_col
        self.ram_detail_text.value = ram_str
        self.ram_bar.value = min(1.0, max(0.0, ram_pct / 100.0))
        self.ram_bar.color = ram_col

    def _metrics_loop(self) -> None:
        while not self._closing:
            time.sleep(3.0)
            if self._closing:
                break
            try:
                with self._ui_lock:
                    self._update_metrics_once()
                    self._refresh()
            except Exception:
                pass

    def _visualizer_loop(self) -> None:
        idle_heights = [10, 16, 24, 14, 28, 20, 12, 26, 18, 30, 15, 22, 12, 25, 16, 10]
        tick = 0.0
        while not self._closing:
            active = self._ui_state in ("listening", "speaking", "processing")
            time.sleep(0.14 if active else 0.7)
            if self._closing or not self._eq_bars:
                continue
            tick += 0.55
            try:
                with self._ui_lock:
                    st = self._ui_state
                    for i, bar in enumerate(self._eq_bars):
                        if st == "listening":
                            wave = math.sin(tick + i * 0.65)
                            bar.height = max(8, min(38, int(22 + wave * 12 + random.randint(-4, 5))))
                            bar.bgcolor = DANGER_FG if i % 2 == 0 else "#FB7185"
                        elif st == "speaking":
                            wave = math.cos(tick * 1.2 + i * 0.55)
                            bar.height = max(8, min(36, int(20 + wave * 11 + random.randint(-3, 4))))
                            bar.bgcolor = ACCENT_CYAN if i % 2 == 0 else ACCENT_INDIGO
                        elif st == "processing":
                            wave = math.sin(tick * 0.9 + i * 0.4)
                            bar.height = max(8, min(28, int(17 + wave * 8)))
                            bar.bgcolor = WARN_FG
                        else:
                            bar.height = idle_heights[i]
                            bar.bgcolor = ACCENT_CYAN if i % 2 == 0 else ACCENT_INDIGO
                    self._refresh()
            except Exception:
                pass

    # --------------------------------------------------------- State & UI
    def _set_state(self, state: str) -> None:
        self._ui_state = state
        theme = STATE_THEMES.get(state, STATE_THEMES["ready"])
        fg = theme["fg"]
        self.state_dot.bgcolor = fg
        self.state_text.value = theme["label"]
        self.state_text.color = fg
        self.state_pill.bgcolor = theme["pill_bg"]
        self.state_pill.border = ft.Border.all(1, theme["border"])

        hero_border = BORDER_ACCENT if state == "ready" else theme["border"]
        self.hero_card.border = ft.Border.all(1, hero_border)
        grad_colors = theme["mic_grad"] if (state != "ready" or not self._busy) else ["#334155", "#1E293B"]
        self.mic_btn.gradient = ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=grad_colors,
        )
        self.mic_halo_inner.bgcolor = theme["halo_inner"]
        self.mic_halo_outer.bgcolor = theme["halo_outer"]

        if state == "listening":
            self.mic_icon.name = ft.Icons.GRAPHIC_EQ_ROUNDED
            self._set_step_style(0, "active")
            if not self._current["command"]:
                self.command_text.value = "جاري الاستماع... تحدث الآن" if self._lang == "ar" else "Listening... Speak now"
                self.command_text.color = DANGER_FG
        elif state == "processing":
            self.mic_icon.name = ft.Icons.HOURGLASS_TOP_ROUNDED
            self._set_step_style(0, "done")
            self._set_step_style(1, "active")
            if not self._current["command"]:
                self.command_text.value = "جاري معالجة الصوت وفهم الأمر..." if self._lang == "ar" else "Processing speech & understanding..."
                self.command_text.color = WARN_FG
        elif state == "speaking":
            self.mic_icon.name = ft.Icons.VOLUME_UP_ROUNDED
        else:
            self.mic_icon.name = ft.Icons.MIC_ROUNDED

    def _update_stepper_labels(self) -> None:
        is_ar = self._lang == "ar"
        for i, (en_lbl, _) in enumerate(PIPELINE_STEPS):
            self._step_labels[i].value = PIPELINE_STEPS_AR[i] if is_ar else en_lbl
            self._step_boxes[i].content.rtl = is_ar
        arrow_icon = ft.Icons.CHEVRON_LEFT_ROUNDED if is_ar else ft.Icons.CHEVRON_RIGHT_ROUNDED
        for arr in self._step_arrows:
            arr.name = arrow_icon
        self.stepper_row.rtl = is_ar
        self.hero_main_row.rtl = is_ar
        self.hero_cmd_header.rtl = is_ar
        self.hero_cmd_col.horizontal_alignment = ft.CrossAxisAlignment.END if is_ar else ft.CrossAxisAlignment.START
        self.chips_container_row.rtl = is_ar
        self.chips_row.rtl = is_ar
        if not self._current["command"]:
            self.command_text.value = "اضغط على الميكروفون وتحدث بالأمر..." if is_ar else "Tap the microphone and speak a command..."
            self.command_text.text_align = ft.TextAlign.RIGHT if is_ar else ft.TextAlign.LEFT

    def _on_lang_change(self, e) -> None:
        if e.control.selected:
            with self._ui_lock:
                self._lang = list(e.control.selected)[0]
                self._rebuild_quick_chips()
                self._update_stepper_labels()
                self._refresh()

    def _on_voice_toggle(self, e) -> None:
        self._voice_on = bool(e.control.value)
        if not self._voice_on:
            speaker.stop()

    def _clear_history(self, _) -> None:
        with self._ui_lock:
            self.history_list.controls.clear()
            self.history_empty.visible = True
            self._refresh()

    def _add_history(self, status: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        label, fg_col, pill_bg = STATUS_BADGES.get(status, (status, TEXT_MUTED, ROW_BG))
        self.history_empty.visible = False
        status_pill = ft.Container(
            content=ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=fg_col),
            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
            border_radius=10,
            bgcolor=pill_bg,
        )
        row = ft.Container(
            content=ft.Row(
                [
                    ft.Text(stamp, size=11, color=TEXT_MUTED, font_family="monospace", width=72),
                    ft.Text(self._current["command"] or "-", size=12, color=TEXT_MAIN, expand=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(self._current["intent"] or "-", size=11, color=ACCENT_INDIGO, expand=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Container(content=status_pill, width=110, alignment=ft.Alignment.CENTER_RIGHT),
                ],
            ),
            bgcolor=ROW_BG,
            border=ft.Border.all(1, BORDER_SUBTLE),
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=8, vertical=5),
        )
        self.history_list.controls.insert(0, row)

    def _on_listen_click(self, _) -> None:
        if self._busy or self._closing:
            return
        with self._ui_lock:
            self._busy = True
            self._current = {"command": "", "intent": ""}
            self._reset_stepper()
            self._set_state("listening")
            self.detected_lang_badge.visible = False
            self.intent_text.value = "-"
            self.intent_text.color = TEXT_MAIN
            self.intent_sub.value = "Analyzing..."
            self.understanding_card.border = ft.Border.all(1, BORDER_SUBTLE)
            self.exec_status_text.value = "Waiting"
            self.exec_status_text.color = TEXT_MUTED
            self.exec_sub.value = ""
            self.execution_card.border = ft.Border.all(1, BORDER_SUBTLE)
            self.result_text.value = ""
            self._refresh()

        threading.Thread(target=self._run_pipeline, args=(self._lang,), daemon=True).start()

    def _run_pipeline(self, language: str) -> None:
        try:
            self.pipeline(self.emit, language, self.confirm)
        except Exception as exc:
            self.emit(Event("error", "failed", f"Unexpected error: {exc}"))
        finally:
            self._tts_queue.join()
            self._busy = False
            self.emit(Event("listening", "ready"))

    def emit(self, event: Event) -> None:
        if event.stage == "result" and self._voice_on and event.text:
            self._tts_queue.put((event.text, event.state))

        with self._ui_lock:
            if self._closing:
                return
            stage, state, text = event.stage, event.state, event.text

            if stage == "listening":
                self._set_state(state)
            elif stage == "command":
                self._current["command"] = text
                self.command_text.value = text
                self.command_text.color = TEXT_MAIN
                self.command_text.text_align = ft.TextAlign.RIGHT if state == "ar" else ft.TextAlign.LEFT
                self.detected_lang_badge.content.value = "العربية" if state == "ar" else "ENGLISH"
                self.detected_lang_badge.visible = True
                self._set_step_style(0, "done")
                self._set_step_style(1, "done")
                self._set_step_style(2, "active")
            elif stage == "understanding":
                self._current["intent"] = text
                self.intent_text.value = text
                self._set_step_style(2, "done")
                if state == "allowed":
                    self.intent_text.color = ACCENT_CYAN
                    self.intent_sub.value = "Validated & Safe"
                    self.understanding_card.border = ft.Border.all(1, BORDER_ACCENT)
                    self._set_step_style(3, "done")
                    self._set_step_style(4, "active")
                elif state == "rejected":
                    self.intent_text.color = DANGER_FG
                    self.intent_sub.value = "Blocked by Security Gate"
                    self.understanding_card.border = ft.Border.all(1, "#6B2B38")
                    self._set_step_style(3, "fail")
                else:
                    self.intent_text.color = WARN_FG
                    self.intent_sub.value = "User Confirmation Required"
                    self.understanding_card.border = ft.Border.all(1, "#6B5224")
                    self._set_step_style(3, "warn")
            elif stage == "execution":
                label, color, _ = STATUS_BADGES.get(state, (EXECUTION_STATUSES.get(state, state), TEXT_MAIN, ROW_BG))
                self.exec_status_text.value = label
                self.exec_status_text.color = color
                if text:
                    self.exec_sub.value = text[:80]
                if state == "completed":
                    self.execution_card.border = ft.Border.all(1, BORDER_ACCENT)
                    self._set_step_style(3, "done")
                    self._set_step_style(4, "done")
                elif state in ("failed", "rejected"):
                    self.execution_card.border = ft.Border.all(1, "#6B2B38")
                    self._set_step_style(4, "fail")
                elif state == "cancelled":
                    self.execution_card.border = ft.Border.all(1, BORDER_SUBTLE)
                    self._set_step_style(3, "fail")
                elif state in ("running", "awaiting_confirmation"):
                    self.execution_card.border = ft.Border.all(1, ACCENT_CYAN)
                    if state == "running":
                        self._set_step_style(3, "done")
                        self._set_step_style(4, "active")
                if state in TERMINAL_EXECUTION:
                    self._add_history(state)
                    self._refresh_workspace_files()
            elif stage == "result":
                self.result_text.value = text
                self.result_text.text_align = ft.TextAlign.RIGHT if state == "ar" else ft.TextAlign.LEFT
            elif stage == "error":
                self._set_state("error")
                self.exec_status_text.value = "Failed"
                self.exec_status_text.color = DANGER_FG
                self.execution_card.border = ft.Border.all(1, "#6B2B38")
                self.result_text.value = text
                self._add_history("failed")

            self._refresh()

    def confirm(self, prompt: str) -> bool:
        done = threading.Event()
        answer = [False]
        if self._voice_on and prompt:
            self._tts_queue.put((prompt, self._lang))

        def finish(val: bool):
            if done.is_set():
                return
            answer[0] = val
            done.set()
            with self._ui_lock:
                self.confirm_overlay.visible = False
                self._refresh()

        with self._ui_lock:
            remaining = [CONFIRM_TIMEOUT_SECONDS]
            self.confirm_prompt_txt.value = prompt
            self.confirm_timer_txt.value = f"Auto-cancel in {remaining[0]}s"
            self.confirm_yes_btn.content.value = "نعم، نفّذ" if self._lang == "ar" else "Confirm"
            self.confirm_no_btn.content.value = "إلغاء" if self._lang == "ar" else "Cancel"
            self.confirm_yes_btn.on_click = lambda _: finish(True)
            self.confirm_no_btn.on_click = lambda _: finish(False)
            self.confirm_overlay.visible = True
            self._refresh()

        def timer_loop():
            while not done.is_set() and remaining[0] > 0:
                time.sleep(1)
                remaining[0] -= 1
                if not done.is_set():
                    with self._ui_lock:
                        self.confirm_timer_txt.value = f"Auto-cancel in {remaining[0]}s"
                        self._refresh()
            if not done.is_set():
                finish(False)

        threading.Thread(target=timer_loop, daemon=True).start()
        done.wait(CONFIRM_TIMEOUT_SECONDS + 3)
        return answer[0]

    def _tts_loop(self) -> None:
        while not self._closing:
            item = self._tts_queue.get()
            try:
                if item is None:
                    return
                msg, lang = item
                if not self._closing and self._voice_on:
                    self.emit(Event("listening", "speaking"))
                    self._speak(msg, lang)
            finally:
                self._tts_queue.task_done()

    def close(self) -> None:
        self._closing = True
        speaker.stop()
        self._tts_queue.put(None)
