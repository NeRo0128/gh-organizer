# src/github_organizer/icons.py
"""Iconos de Nerd Fonts centralizados para toda la aplicación.

Si tu terminal no soporta Nerd Fonts, exporta NO_NERD_FONTS=1
y se usarán emojis como fallback.
"""

import os

import nerdfont as nf

_USE_EMOJI = os.environ.get("NO_NERD_FONTS") == "1"


def icon(name: str, emoji_fallback: str, nf_fallback: str = "?") -> str:
    """Devuelve un icono de Nerd Fonts por nombre, con fallback seguro."""
    if _USE_EMOJI:
        return emoji_fallback
    return nf.icons.get(name, nf_fallback)


# --- Lenguajes de programación ---
LANG_ICONS: dict[str, str] = {
    "Python": icon("dev-python", "🐍"),
    "JavaScript": icon("dev-javascript", "🟨"),
    "TypeScript": icon("dev-typescript", "🔷"),
    "Go": icon("dev-go", "🐹"),
    "Rust": icon("dev-rust", "🦀"),
    "HTML": icon("dev-html5", "🌐"),
    "CSS": icon("dev-css3", "🎨"),
    "Shell": icon("dev-terminal", "🐚"),
    "Java": icon("dev-java", "☕"),
    "C": icon("dev-c", "🔧"),
    "C++": icon("dev-cplusplus", "🔧"),
    "C#": icon("dev-csharp", "🔷"),
    "Ruby": icon("dev-ruby", "💎"),
    "PHP": icon("dev-php", "🐘"),
    "Vue": icon("dev-vuejs", "💚"),
    "Svelte": icon("dev-svelte", "🧡"),
    "Swift": icon("dev-swift", "🦅"),
    "Kotlin": icon("dev-kotlin", "🟣"),
    "Dart": icon("dev-dart", "🎯"),
    "Jupyter Notebook": icon("dev-jupyter", "📓"),
}

# --- Iconos de la interfaz ---
ICON_REPO = icon("cod-repo", "📦")
ICON_FOLDER = icon("cod-folder", "📁")
ICON_FOLDER_OPEN = icon("cod-folder-opened", "📂")
ICON_UNASSIGNED = icon("cod-inbox", "⚠️")
ICON_LOCK = icon("fa-lock", "🔒")
ICON_GLOBE = icon("fa-globe", "🌐")
ICON_USER = icon("fa-user", "👤")
ICON_GITHUB = icon("dev-github", "🐙")
ICON_EMPTY = icon("cod-circle_outline", "○")
ICON_WARNING = icon("fa-warning", "⚠️")
ICON_RELOAD = icon("cod-refresh", "🔄")
