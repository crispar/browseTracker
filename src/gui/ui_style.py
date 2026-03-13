"""UI typography and style helpers for consistent rendering."""

import platform
import tkinter.font as tkfont
from tkinter import ttk


_WINDOWS_FONT_CANDIDATES = (
    "Malgun Gothic",
    "Noto Sans CJK KR",
    "Segoe UI",
    "Arial",
)

_MAC_FONT_CANDIDATES = (
    "Apple SD Gothic Neo",
    "Helvetica Neue",
    "Arial",
)

_LINUX_FONT_CANDIDATES = (
    "Noto Sans CJK KR",
    "Noto Sans",
    "DejaVu Sans",
    "Arial",
)

_GENERIC_FONT_CANDIDATES = (
    "Segoe UI",
    "Arial",
)


def _pick_font_family(available_families, system_name=None):
    """Return the best available UI font family for the current platform."""
    available = {name.lower(): name for name in available_families}

    system = system_name or platform.system()
    if system == "Windows":
        candidates = _WINDOWS_FONT_CANDIDATES
    elif system == "Darwin":
        candidates = _MAC_FONT_CANDIDATES
    elif system == "Linux":
        candidates = _LINUX_FONT_CANDIDATES
    else:
        candidates = _GENERIC_FONT_CANDIDATES

    for candidate in candidates:
        key = candidate.lower()
        if key in available:
            return available[key]

    return "TkDefaultFont"


def apply_global_typography(root):
    """Apply consistent fonts and spacing for better readability."""
    available = set(tkfont.families(root))
    family = _pick_font_family(available, platform.system())

    font_specs = (
        ("TkDefaultFont", 10),
        ("TkTextFont", 10),
        ("TkMenuFont", 10),
        ("TkHeadingFont", 10),
        ("TkCaptionFont", 10),
        ("TkSmallCaptionFont", 9),
        ("TkTooltipFont", 9),
    )

    for name, size in font_specs:
        try:
            named_font = tkfont.nametofont(name)
            named_font.configure(family=family, size=size, weight="normal")
        except Exception:
            # Some Tk distributions do not expose every named font.
            continue

    style = ttk.Style(root)
    style.configure("TButton", padding=(10, 4))
    style.configure("TEntry", padding=(5, 3))
    style.configure("Treeview", rowheight=24)

    setattr(root, "_linktracker_font_family", family)
    return family


def get_body_font(root, size=10):
    """Return standard body font tuple for text-heavy widgets."""
    family = getattr(root, "_linktracker_font_family", None)
    if not family:
        family = apply_global_typography(root)
    return (family, size)
