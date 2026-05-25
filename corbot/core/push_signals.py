"""
Push Notifications utilities.
"""
import json
import logging

logger = logging.getLogger(__name__)


def send_push(subscription, title: str, body: str, url: str = '/commissions'):
    """Envia uma Web Push Notification para um PushSubscription."""
    try:
        from pywebpush import webpush  # type: ignore

        vapid_private_key = _get_vapid_private_key()
        if not vapid_private_key:
            return

        from django.conf import settings as django_settings
        vapid_claims_sub = getattr(django_settings, 'VAPID_CLAIMS_SUB', 'mailto:admin@corbanplus.com')

        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=json.dumps({'title': title, 'body': body, 'url': url}),
            vapid_private_key=vapid_private_key,
            vapid_claims={'sub': vapid_claims_sub},
        )
    except Exception as exc:
        logger.error('Erro ao enviar push (endpoint=%s): %s', subscription.endpoint[:40], exc)


def _get_vapid_private_key():
    from django.conf import settings as django_settings
    key = getattr(django_settings, 'VAPID_PRIVATE_KEY', None)
    if not key:
        logger.debug('VAPID_PRIVATE_KEY não configurada — push ignorado.')
    return key


def notify_commissions_released(user_ids: list, value_total=None):
    """
    Envia push para todos os dispositivos dos usuários cujas comissões foram liberadas.
    Chamado após bulk update de release_status → withdraw_available.
    """
    if not _get_vapid_private_key():
        return
    if not user_ids:
        return

    from core.models import PushSubscription  # evitar importação circular no topo

    subscriptions = PushSubscription.objects.filter(user_id__in=user_ids)
    body = 'Comissão disponível para saque!'
    if value_total is not None:
        body = f'R$ {value_total} disponíveis para saque!'

    for sub in subscriptions:
        send_push(sub, title='Comissão liberada! 💰', body=body, url='/commissions')
