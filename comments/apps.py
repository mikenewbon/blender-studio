from django.apps import AppConfig


class CommentsConfig(AppConfig):
    name = 'comments'

    def ready(self) -> None:
        import comments.signals  # noqa: F401
        from actstream import registry

        registry.register(self.get_model('Comment'))
        registry.register(self.get_model('Like'))
