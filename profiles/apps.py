from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    name = 'profiles'

    def ready(self) -> None:
        import profiles.signals  # noqa: F401
        from actstream import registry
        from django.contrib.auth import get_user_model

        User = get_user_model()

        registry.register(User)
