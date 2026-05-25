from django.apps import AppConfig


class BankConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bank'
    verbose_name = 'Banco'

    def ready(self):
        import bank.signals  # noqa: F401
