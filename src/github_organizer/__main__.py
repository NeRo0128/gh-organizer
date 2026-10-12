# src/github_organizer/__main__.py
def main() -> None:
    # El logging debe configurarse ANTES de importar la app,
    # para que todos los loggers de los módulos hereden la config.
    from github_organizer.utils.logging import setup_logging

    setup_logging()

    from github_organizer.app import GithubOrganizerApp

    app = GithubOrganizerApp()
    app.run()


if __name__ == "__main__":
    main()
