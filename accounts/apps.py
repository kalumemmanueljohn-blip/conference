from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Comptes utilisateurs'

    def ready(self):
        # Import des signaux pour activer la création auto du Profile
        import accounts.signals  # noqa: F401