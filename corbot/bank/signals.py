from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction


UPDATE_ACTIONS = {'UPDATE', 'CSV_IMPORT', 'CSV_UPDATE'}


@receiver(post_save, sender='bank.TableHistory')
def on_table_history_created(sender, instance, created, **kwargs):
    """
    Dispara a geração de sugestões de configuração para todos os grupos de
    comissionamento afetados quando uma tabela bancária é atualizada.
    Usa transaction.on_commit para garantir que o DB já foi confirmado.
    """
    if not created:
        return
    if instance.action not in UPDATE_ACTIONS:
        return

    table_id = str(instance.table_id)
    history_id = str(instance.pk)

    transaction.on_commit(
        lambda: _dispatch_suggestion_task(table_id, history_id)
    )


def _dispatch_suggestion_task(table_id: str, history_id: str):
    try:
        from ai_agent.tasks import generate_suggestions_for_table
        generate_suggestions_for_table.delay(table_id, history_id)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            'Falha ao despachar generate_suggestions_for_table '
            'table_id=%s history_id=%s', table_id, history_id
        )
