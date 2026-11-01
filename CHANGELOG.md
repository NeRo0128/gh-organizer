# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Verificación de dependencias externas (git, keyring, GitHub CLI) al arranque,
  con modal de estado y opciones para continuar o salir.

## [1.1.0] - 2026-11-01

### Added

- Soporte de internacionalización (i18n) en español e inglés con hot-reload
  desde la pantalla de ajustes.

- Pantalla de ayuda (cheat sheet) con los atajos de teclado.

- StatusBar dinámica.

- Workflow de CI (`.github/workflows/ci.yml`) con lint + tests.

### Fixed

- Manejo robusto de errores: las excepciones de PyGithub, OSError y
  Subprocess se traducen a excepciones de dominio; ninguna llega a la UI.

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

[Unreleased]: https://github.com/NeRo0128/gh-organizer/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/NeRo0128/gh-organizer/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/NeRo0128/gh-organizer/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/NeRo0128/gh-organizer/releases/tag/v1.0.0
