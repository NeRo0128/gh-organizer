# src/github_organizer/ui/widgets/repo_detail.py
"""Panel con los detalles del repositorio seleccionado."""

from textual.widgets import Static

from github_organizer.core import Repo
from github_organizer.ui import ICON_GLOBE, ICON_LOCK, ICON_REPO, LANG_ICONS
from github_organizer.utils import format_date


class RepoDetail(Static):
    """Muestra los metadatos del repo o un estado vacío."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.border_title = " Detalles "
        self.show_empty()

    def show_empty(self) -> None:
        self.update(
            "[dim italic]Selecciona un repositorio para ver sus detalles.[/dim italic]"
        )

    def show(self, repo: Repo) -> None:
        icon_char = LANG_ICONS.get(repo.language or "", ICON_REPO)
        lang = f"{icon_char} {repo.language}" if repo.language else "[dim]—[/dim]"
        visibility = f"{ICON_LOCK} Privado" if repo.private else f"{ICON_GLOBE} Público"
        updated = format_date(repo.updated_at)
        description = (
            repo.description
            if repo.description
            else "[dim italic]Sin descripción[/dim italic]"
        )

        self.update(
            f"[b cyan]{icon_char} {repo.name}[/b cyan]\n"
            f"\n"
            f"{description}\n"
            f"\n"
            f"[dim]{'─' * 40}[/dim]\n"
            f"\n"
            f"[b]Lenguaje     [/b]  {lang}\n"
            f"[b]Visibilidad  [/b]  {visibility}\n"
            f"[b]Actualizado  [/b]  {updated}\n"
            f"[b]Ruta         [/b]  [dim]{repo.full_name}[/dim]\n"
            f"\n"
            f"[b]URL          [/b]  [u cyan]{repo.html_url}[/u cyan]\n"
        )
