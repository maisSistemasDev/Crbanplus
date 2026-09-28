"""
Pontos de restauração para o agente IA.

Antes de executar operações destrutivas (delete, update em massa,
normalização, etc.), as ferramentas da IA devem criar um restore point.
O usuário pode depois pedir para desfazer a ação, restabelecendo o estado
anterior o máximo possível.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import models, transaction
from django.forms.models import model_to_dict
from django.utils import timezone

from .models import AIAgentRestorePoint

logger = logging.getLogger(__name__)


class RestorePointError(Exception):
    pass


def _serialize_value(value: Any) -> Any:
    """Converte valores não serializáveis em JSON para tipos seguros."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, models.Model):
        return str(value.pk)
    return str(value)


def serialize_instance(instance: models.Model, extra_fields: dict | None = None) -> dict:
    """
    Serializa uma instância Django em dict.
    Inclui campos próprios do modelo (exceto muitos-para-muitos) e, opcionalmente,
    dados extras (ex.: IDs de relacionamentos M2M).
    """
    data = model_to_dict(instance, exclude=[f.name for f in instance._meta.many_to_many])
    serialized = {k: _serialize_value(v) for k, v in data.items()}
    if extra_fields:
        serialized.update({k: _serialize_value(v) for k, v in extra_fields.items()})
    return serialized


def get_many_to_many_ids(instance: models.Model, field_name: str) -> list[str]:
    """Retorna lista de IDs (string) de um campo M2M."""
    manager = getattr(instance, field_name)
    return [str(pk) for pk in manager.values_list("pk", flat=True)]


def create_restore_point(
    operation_type: str,
    model_label: str,
    description: str,
    instances: list[models.Model] | None = None,
    snapshot_data: dict | None = None,
    conversation_id: int | None = None,
) -> AIAgentRestorePoint:
    """
    Cria um ponto de restauração.

    Passe `instances` para que a função serialize automaticamente, ou
    `snapshot_data` se os dados já estiverem prontos.
    """
    from .models import Conversation

    if snapshot_data is None:
        snapshot_data = {"records": []}
        for instance in instances or []:
            m2m_data = {}
            for field in instance._meta.many_to_many:
                m2m_data[field.name] = get_many_to_many_ids(instance, field.name)
            snapshot_data["records"].append(serialize_instance(instance, m2m_data))

    conversation = None
    if conversation_id:
        try:
            conversation = Conversation.objects.get(pk=conversation_id)
        except Conversation.DoesNotExist:
            pass

    return AIAgentRestorePoint.objects.create(
        conversation=conversation,
        operation_type=operation_type,
        model_label=model_label,
        description=description,
        snapshot_data=snapshot_data,
    )


def _model_from_label(model_label: str) -> type[models.Model]:
    """Resolve 'app_label.ModelName' para a classe do modelo."""
    try:
        return models.apps.get_model(model_label)
    except LookupError as exc:
        raise RestorePointError(f"Modelo '{model_label}' não encontrado.") from exc


def _parse_value(field: models.Field, value: Any) -> Any:
    """Converte um valor serializado de volta para o tipo do campo Django."""
    if value is None:
        return None
    if isinstance(field, models.DateField):
        from datetime import date
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    if isinstance(field, models.DateTimeField):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    if isinstance(field, models.DecimalField):
        try:
            return Decimal(value)
        except Exception:
            return None
    if isinstance(field, models.UUIDField):
        try:
            return uuid.UUID(value)
        except (ValueError, TypeError):
            return None
    if isinstance(field, models.ForeignKey):
        if value is None or value == "":
            return None
        try:
            return field.related_model.objects.get(pk=value)
        except Exception:
            return None
    return value


def restore_restore_point(restore_point_id: str) -> dict:
    """Restaura o estado salvo em um ponto de restauração."""
    try:
        rp = AIAgentRestorePoint.objects.get(pk=restore_point_id, restored_at__isnull=True)
    except AIAgentRestorePoint.DoesNotExist:
        raise RestorePointError(f"Ponto de restauração '{restore_point_id}' não encontrado ou já restaurado.")

    model_label = rp.model_label
    operation_type = rp.operation_type
    snapshot_data = rp.snapshot_data or {}

    restored_count = 0
    errors: list[str] = []

    if operation_type == AIAgentRestorePoint.OPERATION_DELETE and model_label:
        Model = _model_from_label(model_label)
        with transaction.atomic():
            for record in snapshot_data.get("records", []):
                try:
                    data = dict(record)
                    pk = data.pop("id", None)
                    m2m_data = data.pop("_m2m", {}) if "_m2m" in data else {}
                    # Separa FKs dos campos simples
                    prepared: dict[str, Any] = {}
                    for field in Model._meta.fields:
                        if field.name in data:
                            prepared[field.name] = _parse_value(field, data[field.name])

                    obj, created = Model.objects.update_or_create(
                        pk=pk,
                        defaults=prepared,
                    )

                    # Restaura M2M
                    for m2m_field_name, ids in m2m_data.items():
                        field = Model._meta.get_field(m2m_field_name)
                        if not field.many_to_many:
                            continue
                        related_model = field.related_model
                        getattr(obj, m2m_field_name).set(related_model.objects.filter(pk__in=ids))

                    restored_count += 1
                except Exception as exc:
                    logger.exception("Erro ao restaurar registro: %s", exc)
                    errors.append(str(exc))

    elif operation_type == AIAgentRestorePoint.OPERATION_UPDATE and model_label:
        Model = _model_from_label(model_label)
        with transaction.atomic():
            for record in snapshot_data.get("records", []):
                try:
                    data = dict(record)
                    pk = data.pop("id", None)
                    if not pk:
                        continue
                    obj = Model.objects.get(pk=pk)
                    for field in Model._meta.fields:
                        if field.name in data and field.name != obj._meta.pk.name:
                            setattr(obj, field.name, _parse_value(field, data[field.name]))
                    obj.save()
                    restored_count += 1
                except Exception as exc:
                    logger.exception("Erro ao restaurar registro: %s", exc)
                    errors.append(str(exc))

    elif operation_type == AIAgentRestorePoint.OPERATION_NORMALIZE:
        # Normalização: snapshot contém 'merged_groups' com canonical e duplicates.
        # Para desfazer, recriamos os convênios duplicados e movemos as tabelas de volta.
        from bank.models import Agreement, Table, Bank, normalize_name

        with transaction.atomic():
            for group in snapshot_data.get("merged_groups", []):
                try:
                    canonical_id = group["canonical"]["id"]
                    canonical = Agreement.objects.get(pk=canonical_id)
                    for dup_info in group["duplicates"]:
                        dup_id = dup_info["id"]
                        dup_name = dup_info["name"]
                        dup_banks = dup_info.get("banks", [])
                        dup_tables = dup_info.get("tables", [])

                        new_dup = Agreement.objects.create(name=dup_name)
                        for bank_id in dup_banks:
                            try:
                                bank = Bank.objects.get(pk=bank_id)
                                new_dup.banks.add(bank)
                            except Bank.DoesNotExist:
                                pass

                        for table_id in dup_tables:
                            try:
                                table = Table.objects.get(pk=table_id)
                                table.agreement = new_dup
                                table.save(update_fields=["agreement"])
                            except Table.DoesNotExist:
                                pass

                        # Remove o vínculo do canonical com os bancos que pertenciam apenas ao duplicado
                        # (simplificação: deixamos como está; o usuário pode ajustar depois)
                    restored_count += 1
                except Exception as exc:
                    logger.exception("Erro ao desfazer normalização: %s", exc)
                    errors.append(str(exc))

    else:
        raise RestorePointError(f"Restauração automática não implementada para operação '{operation_type}'.")

    rp.restored_at = timezone.now()
    rp.save(update_fields=["restored_at"])

    return {
        "success": True,
        "restore_point_id": str(rp.id),
        "restored_count": restored_count,
        "errors": errors,
    }


def list_restore_points(limit: int = 20) -> list[dict]:
    """Lista os pontos de restauração mais recentes não restaurados."""
    qs = AIAgentRestorePoint.objects.filter(restored_at__isnull=True).order_by("-created_at")[:limit]
    return [
        {
            "id": str(rp.id),
            "operation_type": rp.operation_type,
            "model_label": rp.model_label,
            "description": rp.description,
            "created_at": rp.created_at.isoformat(),
        }
        for rp in qs
    ]
