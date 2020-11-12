from django.apps import AppConfig


class BlogConfig(AppConfig):
    name = 'blog'

    def ready(self) -> None:
        import blog.signals  # noqa: F401
        from actstream import registry

        registry.register(self.get_model('Post'))
