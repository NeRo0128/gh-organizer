# src/github_organizer/ui/styles/themes.py
"""Definición de los temas de la aplicación.

Cada tema se registra con `App.register_theme()` y se activa con
`App.theme = "<name>"`. El orden de ALL_THEMES define el ciclo de ctrl+t.
"""

from textual.theme import Theme

# ──────────────────────────────────────────────────────────────────── #
#  GitHub — paleta oficial de GitHub Dark
#  https://primer.style/foundations/color
# ──────────────────────────────────────────────────────────────────── #
GITHUB_DARK = Theme(
    name="github",
    primary="#58a6ff",
    secondary="#8b949e",
    accent="#f78166",
    foreground="#c9d1d9",
    background="#0d1117",
    success="#3fb950",
    warning="#d29922",
    error="#f85149",
    surface="#161b22",
    panel="#21262d",
    boost="#30363d",
    dark=True,
    variables={
        "border": "#30363d",
        "border-blurred": "#21262d",
        "footer-background": "#161b22",
        "footer-key-foreground": "#58a6ff",
        "input-selection-background": "#58a6ff 35%",
        "block-cursor-foreground": "#0d1117",
        "block-cursor-background": "#58a6ff",
    },
)


# ──────────────────────────────────────────────────────────────────── #
#  Tokyo Night — https://github.com/enkia/tokyo-night-vscode-theme
# ──────────────────────────────────────────────────────────────────── #
TOKYO_NIGHT = Theme(
    name="tokyo-night",
    primary="#7aa2f7",
    secondary="#bb9af7",
    accent="#7dcfff",
    foreground="#c0caf5",
    background="#1a1b26",
    success="#9ece6a",
    warning="#e0af68",
    error="#f7768e",
    surface="#16161e",
    panel="#24283b",
    boost="#292e42",
    dark=True,
    variables={
        "border": "#414868",
        "border-blurred": "#24283b",
        "footer-background": "#16161e",
        "footer-key-foreground": "#7aa2f7",
        "input-selection-background": "#7aa2f7 35%",
        "block-cursor-foreground": "#1a1b26",
        "block-cursor-background": "#7aa2f7",
    },
)


# ──────────────────────────────────────────────────────────────────── #
#  Catppuccin Mocha — https://github.com/catppuccin/catppuccin
# ──────────────────────────────────────────────────────────────────── #
CATPPUCCIN_MOCHA = Theme(
    name="catppuccin-mocha",
    primary="#89b4fa",
    secondary="#cba6f7",
    accent="#94e2d5",
    foreground="#cdd6f4",
    background="#1e1e2e",
    success="#a6e3a1",
    warning="#f9e2af",
    error="#f38ba8",
    surface="#181825",
    panel="#313244",
    boost="#45475a",
    dark=True,
    variables={
        "border": "#585b70",
        "border-blurred": "#313244",
        "footer-background": "#181825",
        "footer-key-foreground": "#89b4fa",
        "input-selection-background": "#89b4fa 35%",
        "block-cursor-foreground": "#1e1e2e",
        "block-cursor-background": "#89b4fa",
    },
)


# ──────────────────────────────────────────────────────────────────── #
#  GitHub Light — paleta clara oficial de GitHub
# ──────────────────────────────────────────────────────────────────── #
GITHUB_LIGHT = Theme(
    name="github-light",
    primary="#0969da",
    secondary="#6e7781",
    accent="#cf222e",
    foreground="#1f2328",
    background="#ffffff",
    success="#1a7f37",
    warning="#9a6700",
    error="#cf222e",
    surface="#f6f8fa",
    panel="#eaeef2",
    boost="#d0d7de",
    dark=False,
    variables={
        "border": "#d0d7de",
        "border-blurred": "#eaeef2",
        "footer-background": "#f6f8fa",
        "footer-key-foreground": "#0969da",
        "input-selection-background": "#0969da 35%",
        "block-cursor-foreground": "#ffffff",
        "block-cursor-background": "#0969da",
    },
)


# El orden define el ciclo de ctrl+t
ALL_THEMES: list[Theme] = [
    GITHUB_DARK,
    TOKYO_NIGHT,
    CATPPUCCIN_MOCHA,
    GITHUB_LIGHT,
]
