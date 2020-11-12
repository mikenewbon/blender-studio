from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    name = 'profiles'

    def ready(self) -> None:
        import profiles.signals  # noqa: F401
        from actstream import registry
        from django.contrib.auth.models import User

        registry.register(User)
