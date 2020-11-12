from django.apps import AppConfig


class TrainingConfig(AppConfig):
    name = 'training'

    def ready(self) -> None:
        import training.signals  # noqa: F401
        from actstream import registry

        registry.register(self.get_model('Section'))
