# src/gh_organizer/ui/widgets/repo_tree.py
"""Árbol de repositorios organizados en carpetas."""

import logging

from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from gh_organizer.core import Repo
from gh_organizer.services import FolderManager
from gh_organizer.services.preferences import get as pref_get
from gh_organizer.services.tree_state import (
    MODE_COLLAPSED,
    MODE_EXPANDED,
    MODE_REMEMBER,
    load_expanded_paths,
    save_expanded_paths,
)
from gh_organizer.ui import (
    ICON_EMPTY,
    ICON_FOLDER,
    ICON_LOCK,
    ICON_REPO,
    ICON_UNASSIGNED,
    LANG_ICONS,
)

logger = logging.getLogger(__name__)


class RepoHighlighted(Message):
    """Emitido cuando el cursor del árbol se posa sobre un nodo."""

    def __init__(self, repo: Repo | None) -> None:
        self.repo = repo
        super().__init__()


class RepoActivated(Message):
    """Emitido cuando el usuario pulsa Enter sobre un repo."""

    def __init__(self, repo: Repo) -> None:
        self.repo = repo
        super().__init__()


class RepoTree(Tree):
    """Árbol con `Sin asignar` + `Colecciones`, navegación left/right y persistencia."""

    def __init__(self, **kwargs) -> None:
        super().__init__("Repositorios", **kwargs)
        self.show_root = False
        self.border_title = " Repositorios "
        self._expanded_paths: set[str] = self._load_initial_paths()
        # 👈 Fuente de verdad: datos sin filtrar
        self._all_repos: list[Repo] = []
        self._all_folder_data: dict[str, list[str]] = {}

    # ---------------------------------------------------------------- #
    #  Estado de expansión
    # ---------------------------------------------------------------- #
    def _load_initial_paths(self) -> set[str]:
        mode = pref_get("tree_mode", MODE_REMEMBER)
        if mode == MODE_COLLAPSED:
            logger.debug("tree_state: modo collapsed")
            return set()
        if mode == MODE_EXPANDED:
            folders = set(FolderManager().get_all().keys())
            logger.debug("tree_state: modo expanded (%d rutas)", len(folders))
            return folders
        return load_expanded_paths()

    def get_expanded_paths(self) -> set[str]:
        return set(self._expanded_paths)

    def set_expanded_paths(self, paths: set[str]) -> None:
        """Sobrescribe el estado de expansión (usado por auto-organizar)."""
        self._expanded_paths = set(paths)
        save_expanded_paths(self._expanded_paths)

    def expand_folder(self, folder_path: str) -> None:
        """Añade una ruta (y sus padres) al set expandido y persiste."""
        if not folder_path:
            return
        parts = folder_path.split("/")
        for i in range(1, len(parts) + 1):
            self._expanded_paths.add("/".join(parts[:i]))
        save_expanded_paths(self._expanded_paths)

    # ---------------------------------------------------------------- #
    #  API pública: rebuild (guarda datos) y filter (renderiza)
    # ---------------------------------------------------------------- #
    def rebuild(
        self,
        repos: list[Repo],
        folder_data: dict[str, list[str]],
    ) -> None:
        """Actualiza la fuente de verdad y renderiza SIN filtro."""
        logger.debug("rebuild: %d repos, %d carpetas", len(repos), len(folder_data))
        self._all_repos = list(repos)
        self._all_folder_data = {k: list(v) for k, v in folder_data.items()}
        self._draw(self._all_repos, self._all_folder_data)  # 👈 antes _render

    def filter(self, query: str) -> None:
        """Aplica un filtro sobre los datos ORIGINALES y renderiza."""
        query = query.strip().lower()

        if not query:
            self._draw(self._all_repos, self._all_folder_data)  # 👈 antes _render
            return

        # 1. Filtrar repos
        filtered_repos = [
            r
            for r in self._all_repos
            if query in r.name.lower() or query in (r.language or "").lower()
        ]

        if not filtered_repos:
            self.clear()
            self.root.add_leaf("[dim italic]Sin resultados[/dim italic]")
            return

        # 2. Filtrar carpetas: solo las que tengan algún repo filtrado
        filtered_names = {r.name for r in filtered_repos}
        new_folder_data: dict[str, list[str]] = {}
        for folder, repo_names in self._all_folder_data.items():
            matching = [name for name in repo_names if name in filtered_names]
            if matching:
                new_folder_data[folder] = matching

        # 3. Renderizar con los datos filtrados (sin tocar los originales)
        self._draw(filtered_repos, new_folder_data)  # 👈 antes _render

    # ---------------------------------------------------------------- #
    #  Render interno
    # ---------------------------------------------------------------- #
    def _draw(  # 👈 antes _render
        self,
        repos: list[Repo],
        folder_data: dict[str, list[str]],
    ) -> None:
        """Dibuja el árbol con los datos dados (no modifica _all_*)."""
        self.clear()

        assigned: set[str] = set()
        for names in folder_data.values():
            assigned.update(names)
        unassigned = [r for r in repos if r.name not in assigned]
        repos_by_name = {r.name: r for r in repos}

        self._expanded_paths &= self._all_valid_paths(folder_data)
        save_expanded_paths(self._expanded_paths)

        if unassigned:
            node = self.root.add(
                f"{ICON_UNASSIGNED} Sin asignar [dim]({len(unassigned)})[/dim]",
                expand=True,
            )
            for repo in sorted(unassigned, key=lambda r: r.name.lower()):
                node.add_leaf(self._repo_label(repo), data=repo)

        if folder_data:
            root = self.root.add(
                f"{ICON_FOLDER} Colecciones [dim]({len(folder_data)})[/dim]",
                expand=True,
            )
            self._build_folder_tree(root, folder_data, repos_by_name)

        self.border_title = f" Repositorios · {len(repos)} "
        logger.debug(
            "Render: %d repos, %d carpetas, %d expandidas",
            len(repos),
            len(folder_data),
            len(self._expanded_paths),
        )

    def _build_folder_tree(
        self,
        root: TreeNode,
        folder_data: dict[str, list[str]],
        repos_by_name: dict[str, Repo],
    ) -> None:
        nodes: dict[tuple, TreeNode] = {(): root}
        for path in sorted(folder_data.keys()):
            parts = path.split("/")
            for i in range(1, len(parts) + 1):
                partial = tuple(parts[:i])
                if partial not in nodes:
                    parent = nodes[partial[:-1]]
                    full_path = "/".join(parts[:i])
                    node = parent.add(
                        f"{ICON_FOLDER} {parts[i - 1]}",
                        expand=full_path in self._expanded_paths,
                    )
                    node.data = full_path
                    nodes[partial] = node

            folder_node = nodes[tuple(parts)]
            repos_in = folder_data[path]
            if not repos_in:
                folder_node.add_leaf(f"[dim italic]{ICON_EMPTY} (vacía)[/dim italic]")
                continue
            for repo_name in repos_in:
                repo = repos_by_name.get(repo_name)
                if repo:
                    folder_node.add_leaf(self._repo_label(repo), data=repo)
                else:
                    folder_node.add_leaf(f"[dim]? {repo_name} (no encontrado)[/dim]")

    @staticmethod
    def _repo_label(repo: Repo) -> str:
        icon_char = LANG_ICONS.get(repo.language or "", ICON_REPO)
        lock = f" [yellow]{ICON_LOCK}[/yellow]" if repo.private else ""
        return f"{icon_char} {repo.name}{lock}"

    @staticmethod
    def _all_valid_paths(folder_data: dict[str, list[str]]) -> set[str]:
        paths: set[str] = set()
        for path in folder_data:
            parts = path.split("/")
            for i in range(1, len(parts) + 1):
                paths.add("/".join(parts[:i]))
        return paths

    @staticmethod
    def paths_with_content(folder_data: dict[str, list[str]]) -> set[str]:
        paths: set[str] = set()
        for path, repos in folder_data.items():
            if not repos:
                continue
            parts = path.split("/")
            for i in range(1, len(parts) + 1):
                paths.add("/".join(parts[:i]))
        return paths

    # ---------------------------------------------------------------- #
    #  Selección
    # ---------------------------------------------------------------- #
    def get_selected_repo(self) -> Repo | None:
        node = self.cursor_node
        if node is None:
            return None
        return node.data if isinstance(node.data, Repo) else None

    # ---------------------------------------------------------------- #
    #  Eventos
    # ---------------------------------------------------------------- #
    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        node = event.node
        repo = node.data if isinstance(node.data, Repo) else None
        self.post_message(RepoHighlighted(repo))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if isinstance(node.data, Repo):
            self.post_message(RepoActivated(node.data))

    def on_key(self, event) -> None:
        if not self.has_focus:
            return
        key = event.key.lower()
        if key == "left":
            event.stop()
            self._cursor_left()
        elif key == "right":
            event.stop()
            self._cursor_right()

    def _cursor_left(self) -> None:
        node = self.cursor_node
        if node is None:
            return
        if node.children and node.is_expanded:
            node.collapse()
            if isinstance(node.data, str) and node.data:
                self._expanded_paths.discard(node.data)
                save_expanded_paths(self._expanded_paths)
        elif node.parent is not None and node.parent is not self.root:
            self.select_node(node.parent)

    def _cursor_right(self) -> None:
        node = self.cursor_node
        if node is None:
            return
        if node.children and not node.is_expanded:
            node.expand()
            if isinstance(node.data, str) and node.data:
                self._expanded_paths.add(node.data)
                save_expanded_paths(self._expanded_paths)
        elif node.children and node.is_expanded:
            self.select_node(node.children[0])
