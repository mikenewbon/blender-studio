from django.apps import AppConfig


class CharactersConfig(AppConfig):
    name = 'characters'

    def ready(self) -> None:
        import characters.signals  # noqa: F401
        from actstream import registry

        registry.register(self.get_model('CharacterVersion'))
        registry.register(self.get_model('CharacterShowcase'))
