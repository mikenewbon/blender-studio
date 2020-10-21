from django.apps import AppConfig


class CommentsConfig(AppConfig):
    name = 'comments'

    def ready(self) -> None:
        import comments.signals  # noqa: F401
