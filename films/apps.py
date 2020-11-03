from django.apps import AppConfig


class FilmConfig(AppConfig):
    name = 'films'

    def ready(self) -> None:
        import films.signals  # noqa: F401
