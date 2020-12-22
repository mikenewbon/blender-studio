from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'
    verbose_name = 'Authentication and authorization'

    def ready(self) -> None:
        import users.signals  # noqa: F401
        from actstream import registry
        from django.contrib.auth import get_user_model

        User = get_user_model()

        registry.register(User)
