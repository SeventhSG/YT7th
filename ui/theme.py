"""Shared design tokens for the dark modern theme."""

# Surfaces - layered dark with subtle elevation
BG = "#0a0a0c"          # app background, deepest
SIDEBAR = "#0f0f12"     # sidebar
CARD = "#16161b"        # raised cards / inputs
CARD_HOVER = "#1f1f26"
ELEVATED = "#1b1b21"    # secondary raised surface

# Text
TEXT = "#f2f2f4"
TEXT_DIM = "#7d7d87"
TEXT_FAINT = "#56565f"

# Accent - dark red
ACCENT = "#9b0e0e"
ACCENT_HOVER = "#c01414"
ACCENT_SOFT = "#2a0d0d"  # tinted background for active states
DANGER = "#c01414"
SUCCESS = "#2e9e5b"

# Lines
BORDER = "#222229"
BORDER_SOFT = "#1a1a20"

import sys

if sys.platform == "darwin":
    FONT = "SF Pro Text"      # falls back to system UI font if unavailable
elif sys.platform == "win32":
    FONT = "Segoe UI"
else:
    FONT = "DejaVu Sans"

# Type scale
H1 = (FONT, 28, "bold")
H2 = (FONT, 17, "bold")
BODY = (FONT, 13)
SMALL = (FONT, 11)
LABEL = (FONT, 12)

# Shared button styles - splat into CTkButton: **theme.BTN_PRIMARY
BTN_PRIMARY = {"fg_color": ACCENT, "hover_color": ACCENT_HOVER,
               "text_color": TEXT, "corner_radius": 10}
BTN_GHOST = {"fg_color": ELEVATED, "hover_color": CARD_HOVER,
             "text_color": TEXT, "corner_radius": 10}
BTN_DANGER = {"fg_color": "transparent", "hover_color": ACCENT_SOFT,
              "border_width": 1, "border_color": DANGER,
              "text_color": DANGER, "corner_radius": 10}
