from django.apps import AppConfig


class FilmConfig(AppConfig):
    name = 'films'

    def ready(self) -> None:
        import films.signals  # noqa: F401
        from actstream import registry

        registry.register(self.get_model('Asset'))
