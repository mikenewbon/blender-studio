from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    name = 'subscriptions'

    def ready(self) -> None:
        import subscriptions.signals  # noqa: F401
