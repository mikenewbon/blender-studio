from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = 'search'

    def ready(self) -> None:
        import search.signals
