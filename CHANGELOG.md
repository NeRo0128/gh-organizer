# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Planned for v1.2.0: editor integration, batch git operations, remote search,
multi-account support. See [Issues](https://github.com/NeRo0128/gh-organizer/issues)._

## [1.1.1] - 2026-11-02

### Fixed

- **Packaging (critical)**: the `[tool.hatch.build.targets.sdist]` section
  restricted the source distribution to only `.py` and `.tcss` files,
  overriding Hatchling's default behavior. As a result, the wheel published
  to PyPI (v1.1.0) was missing `__main__.py` and dozens of other modules,
  causing `ModuleNotFoundError: No module named 'gh_organizer.__main__'`
  when installing from PyPI with `uv tool install` or `pip install`.

  Now the sdist includes the full `src/gh_organizer/` tree by default
  (verified: 46 `.py` files + 5 `.tcss` + 2 `.mo` in the wheel).

### Changed

- **CI**: new `verify-wheel` job that builds the wheel, asserts that
  `__main__.py` and the static files (`.tcss`/`.mo`) are present, and
  installs the wheel in a fresh venv to smoke-test the entry point. This
  prevents regressions like the v1.1.0 → v1.1.1 issue from reaching PyPI.

- **CI**: `ruff` and `pytest-cov` moved into `[dependency-groups] dev` so
  that `uv sync --frozen` (used by CI) installs them. Before they were only
  in `[project.optional-dependencies]`, which `uv sync` does not install,
  causing `Failed to spawn: ruff` in GitHub Actions.

## [1.1.0] - 2026-11-02

### Added

- **Dependency detection** (#16): at startup the app checks for `git` (critical),
  `keyring` and `gh` CLI (optional). On Linux it detects the distro (Arch/Debian/
  Fedora) to show the correct install command. If `git` is missing, a blocking
  modal offers to continue anyway or exit. Global shortcut `Ctrl+D` reopens it.

- **Logs modal** (#18): a new screen accessible with `Ctrl+L` (or from
  _Settings → Avanzado → Ver logs_) shows the last 200 lines of `app.log`,
  color-coded by level (DEBUG, INFO, WARNING, ERROR). Buttons to copy to the
  clipboard (`wl-copy`/`xclip`/`xsel`/`pbcopy`), open the folder, refresh, and
  close. Auto-refresh with `r`, copy with `c`, open folder with `o`.

- **Advanced settings section**: version, config path, open config folder,
  view logs, view releases on GitHub, and "Reset preferences" with
  double-Enter confirmation.

- **PyPI Trusted Publishing** (#12): the release workflow now publishes the
  wheel and sdist to PyPI automatically when a `v*` tag is pushed, using OIDC
  (no manual token required).

- **i18n catalogs**: 224 entries in Spanish and English (0 untranslated).

### Changed

- **Settings redesign**: unified topbar with MainScreen, contextual `StatusBar`
  (instead of the tall `Footer`), and section "Avanzado". Account info is now
  loaded in a background worker, so the screen opens instantly.

- **Hot-reload i18n**: switching language in Settings recomposes the current
  screen and resets the dirty flag correctly (bug fixed).

- **Wheel packaging**: `.tcss` styles and `.mo` catalogs are now shipped inside
  the wheel and the AppImage. Windows workflow uses the correct path separator
  (`;`) for `--add-data`.

- **`platformdirs`** is now declared as a direct dependency (it was transitive
  through Textual).

### Fixed

- `NoActiveAppError` raised when closing Settings during account loading
  (worker now checks `is_mounted` before calling back to the UI).
- `i18n_dirty` was being reset to `True` instead of `False` in
  `MainScreen.on_screen_resume`, causing unnecessary recompositions.
- `auth.tcss` was not found in the packaged wheel/AppImage (moved to
  `ui/styles/` and added to `force-include`).
- Two orphan msgids removed from catalogs (`Ver logs (próximamente)`,
  `Próximamente: visor de logs`); unified under `Ver logs`.

## [1.0.1] - 2026-10-21

### Added

- Auto-organización de repositorios por lenguaje, visibilidad o ambos.
- Paneles de commits y releases en la vista de detalle.
- Persistencia de la organización en un único archivo TOML.

### Fixed

- Fix del AppImage que no incluía los estilos CSS.

## [1.0.0]

### Added

- Lanzamiento inicial: TUI para organizar repositorios de GitHub en
  colecciones personalizadas.

## Tipos de cambios

- **Added** para nuevas funcionalidades.
- **Changed** para cambios en funcionalidades existentes.
- **Deprecated** para funcionalidades pronto obsoletas.
- **Removed** para funcionalidades eliminadas.
- **Fixed** para correcciones de errores.
- **Security** para vulnerabilidades corregidas.

[Unreleased]: https://github.com/NeRo0128/gh-organizer/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/NeRo0128/gh-organizer/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/NeRo0128/gh-organizer/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/NeRo0128/gh-organizer/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/NeRo0128/gh-organizer/releases/tag/v1.0.0
