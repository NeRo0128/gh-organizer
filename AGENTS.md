# AGENTS.md

Textual TUI (`gh-organizer`) that organizes GitHub repos into custom collections.
`src/` layout, package `gh_organizer`, Python **3.14 only** (`requires-python >=3.14`),
managed with `uv` + `uv_build`.

## Commands

```bash
uv sync                                  # install (needs Python 3.14)
uv run gh-organizer                      # launch the TUI
GH_ORG_LOG=DEBUG uv run gh-organizer     # debug; log level lives in GH_ORG_LOG
ruff check src tests                     # lint (see warning below)
```

- **Never run `ruff check .` at the repo root.** `build/AppDir/` contains a vendored
  CPython 3.14 stdlib and turns ~5k files into errors (`--exclude build,dist` if needed).
- `ruff` is *not* a project dependency and there is no ruff config file: the binary on
  `PATH` (`/usr/bin/ruff`) is used with default settings, so formatting/import-order
  opinions in it are not enforced by CI.
- There is no CI test/lint job. Only `.github/workflows/release.yml`, triggered by
  pushing a `v*` tag; nothing runs on normal pushes or PRs.

## Tests are currently broken (not just flaky)

`pytest` is not in `uv.lock`/the `dev` group, so `uv run pytest` fails immediately. The
suite is also **stale**: `tests/*` still imports `github_organizer.*` (old package name,
renamed to `gh_organizer`) and `tests/conftest.py` patches `settings.FOLDERS_FILE` /
`tree_state.TREE_STATE_FILE`, which no longer exist (persistence moved to `config.toml`).
To get a working suite: `uv add --dev pytest`, rewrite imports, and rework
`tmp_data_dirs` to redirect `services.config.CONFIG_FILE` instead.

## Persistence: one TOML file, read-modify-write

- Real path is `~/.config/github-organizer/config.toml` (`platformdirs`, `APP_NAME =
  "github-organizer"` in `services/settings.py`). The README's
  `~/.config/gh-organizer/config.toml` and its example keys are inaccurate.
- Sections: `preferences`, `folders` (`"Work/Web"` → `[repo names]`), `tree_state`.
  Every writer does `config.load()` → mutate one section → `config.save(full_config)`;
  keep that pattern (a partial save would drop the other sections).
- `services/settings.py::load_folders/save_folders` (JSON `folders.json`) is legacy dead
  code — `FolderManager` uses `config.toml`. Do not extend or reuse it.
- Logs go to `~/.local/state/github-organizer/log/app.log` (rotating). Textual owns
  stdout/stderr, so `print()` is invisible — use `logger` or the `StatusBar` widget.

## Architecture

- `__main__.py` calls `setup_logging()` **before** importing `app` so every module logger
  inherits the handler.
- `app.py` registers themes from `ui/styles/themes.py`, then pushes `TokenScreen` or
  `MainScreen` depending on `load_token()`. Token order: `GITHUB_TOKEN` env →
  `gh auth token` → system keyring.
- Layers: `core/models.py` dataclasses (`Repo`, `Folder`, `Commit`, `Release`) ·
  `services/` domain logic + persistence + PyGithub/git wrappers · `ui/screens/` full
  screens · `ui/modals/` `ModalScreen`s · `ui/widgets/` reusable widgets.
- `services/organizer.py` strategies are pure functions `(list[Repo]) ->
  {folder_path: [names]}` and must be registered in `STRATEGIES` to show up in the
  auto-organize modal.
- Blocking work (GitHub API, `git clone`) goes through `@work(thread=True)` plus
  `app.call_from_thread(...)`; never call these services on the UI thread.
- `GitHubClient.list_repos()` uses `type="owner"` on purpose: organization repos are
  excluded by design.
- Shortcuts have a single source of truth: `ui/keybindings.py`. `HelpModal` renders its
  grid from those lists automatically — add bindings there, never hand-write help text.
- `.tcss` files are loaded from disk via `CSS_PATH` (`ui/styles/__init__.py`). Any new
  style file/asset must also be added to the PyInstaller `--add-data` flags in
  `.github/workflows/release.yml`, or the one-file binary crashes at startup.

## Preferences are half-wired

`services/preferences.py` defines `DEFAULTS`, but only `theme`, `tree_mode`, and
`clone_dir` are actually consumed. Everything in `PENDING_SETTINGS` (surfaced via
`is_pending()`) persists and appears in the Settings screen without effect — e.g.
`commits_limit`/`releases_limit` are hardcoded `5` in the panels. Remove a key from
`PENDING_SETTINGS` when you wire it up.

## Conventions

- Spanish everywhere: UI strings, docstrings, log messages, default folder names
  (`Personal`, `Trabajo`, …), and commit messages in Conventional Commits
  (`feat(release): añadir AppImage al workflow`).
- Most modules start with `# src/gh_organizer/<path>.py` as the first line; follow it.
- Folder paths are `/`-joined strings; `FolderManager.create_folder` creates every
  intermediate parent and `delete_folder`/`rename_folder` operate on the whole subtree.
- `build/`, `pylock.toml`, `pylock.build.toml`, `.SRCINFO` are local build artifacts and
  are not in `.gitignore` — never `git add -A`. `dist/` ignores itself.
- AppImage build: `uv run python -m appimage.ctl init|lock|build`, configured under
  `[tool.appimage]` in `pyproject.toml` (interpreter/runtime hashes are pinned there).
