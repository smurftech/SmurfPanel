"""Smurftech design tokens consumed by SmurfPanel.

Source of truth:
    smurftech/brand-devkit/brands/smurftech/tokens/smurftech.tokens.json

This module is intentionally small and semantic. SmurfPanel should consume the
brand language without taking a runtime dependency on the Brand DevKit repo.
When canonical tokens change, update this snapshot and the provenance marker
below as part of the same design-system rollout.
"""

from __future__ import annotations


BRAND_DEVKIT_SOURCE = "brands/smurftech/tokens/smurftech.tokens.json"
BRAND_DEVKIT_REVISION = "f1d9490fdffc726950d3301beda96bcd135fe4ca"

SMURFTECH_COLORS = {
    "deep_night": "#0C111A",
    "night_slate": "#121826",
    "steel_blue": "#1E2A3A",
    "electric_blue": "#0D6EFD",
    "cyan_accent": "#4FC3FF",
    "ice_blue": "#E6F0FF",
    "clean_white": "#F2F4F7",
}

SMURFTECH_RADII = {
    "small": "6px",
    "medium": "8px",
    "large": "12px",
}

SMURFTECH_BORDERS = {
    "default": SMURFTECH_COLORS["steel_blue"],
    "active": SMURFTECH_COLORS["electric_blue"],
}

# Product-level semantic states extend the core Smurftech tokens. These are
# intentionally kept here rather than promoted to the brand layer until more
# than one Smurftech product proves the same state treatment is useful.
SMURFPANEL_STATES = {
    "success_surface": "#18302D",
    "success_border": "#35D0BA",
    "success_text": "#A9FFF2",
    "warning_surface": "#332B18",
    "warning_border": "#F7C948",
    "warning_text": "#FFE8A3",
    "danger_surface": "#3A1F26",
    "danger_border": "#FF5A67",
    "danger_text": "#FFB3BA",
    "muted_text": "rgba(230, 240, 255, 0.68)",
    "disabled_text": "rgba(230, 240, 255, 0.38)",
}


def style_tokens() -> dict[str, str]:
    """Return the flattened token map used by the Qt stylesheet."""

    return {
        **SMURFTECH_COLORS,
        "radius_small": SMURFTECH_RADII["small"],
        "radius_medium": SMURFTECH_RADII["medium"],
        "radius_large": SMURFTECH_RADII["large"],
        "border_default": SMURFTECH_BORDERS["default"],
        "border_active": SMURFTECH_BORDERS["active"],
        **SMURFPANEL_STATES,
    }
