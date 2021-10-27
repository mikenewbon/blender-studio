from django.apps import AppConfig


class CharactersConfig(AppConfig):
    name = 'characters'

    def ready(self) -> None:
        from actstream import registry

        registry.register(self.get_model('CharacterVersion'))
        registry.register(self.get_model('CharacterShowcase'))
