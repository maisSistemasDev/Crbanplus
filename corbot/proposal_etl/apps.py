from django.apps import AppConfig


class ProposalEtlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'proposal_etl'
    verbose_name = 'ETL de Propostas'
