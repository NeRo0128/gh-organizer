# src/github_organizer/ui/widgets/__init__.py
"""Widgets reutilizables que componen las pantallas."""

from github_organizer.ui.widgets.commits_panel import CommitsPanel
from github_organizer.ui.widgets.repo_detail import RepoDetail
from github_organizer.ui.widgets.repo_tree import RepoHighlighted, RepoTree

__all__ = ["CommitsPanel", "RepoDetail", "RepoHighlighted", "RepoTree"]
