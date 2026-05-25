import logging
import json
import os
import datetime
from decimal import Decimal
import uuid

import pandas as pd
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .services import AuditService, LogService

logger = logging.getLogger(__name__)


class LoggingMixin:
    """Mixin para logging e auditoria em views."""

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    def log_info(self, request, action, message, data=None):
        return LogService.info(
            user=request.user, action=action, message=message, data=data,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    def log_error(self, request, action, message, data=None):
        return LogService.error(
            user=request.user, action=action, message=message, data=data,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    def log_warning(self, request, action, message, data=None):
        return LogService.warning(
            user=request.user, action=action, message=message, data=data,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    def log_debug(self, request, action, message, data=None):
        return LogService.debug(
            user=request.user, action=action, message=message, data=data,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    def audit_create(self, request, instance, data_after=None):
        return AuditService.log_create(
            user=request.user, instance=instance, data_after=data_after,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    def audit_update(self, request, instance, data_before=None, data_after=None):
        return AuditService.log_update(
            user=request.user, instance=instance,
            data_before=data_before, data_after=data_after,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    def audit_delete(self, request, instance, data_before=None):
        return AuditService.log_delete(
            user=request.user, instance=instance, data_before=data_before,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )


class FileProcessingMixin:
    """Mixin para processamento de arquivos (JSON, CSV, Excel)."""

    def save_file(self, file, path=None, prefix='upload'):
        if not file:
            raise ValueError("Arquivo não fornecido")
        ext = os.path.splitext(file.name)[1]
        unique_filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(path, unique_filename) if path else unique_filename
        return default_storage.save(save_path, ContentFile(file.read()))

    def read_json_file(self, file):
        try:
            content = file.read().decode('utf-8')
            return json.loads(content)
        except Exception as e:
            raise ValueError(f"Erro ao processar arquivo JSON: {str(e)}")

    def read_excel_file(self, file, sheet_name=0):
        try:
            df = pd.read_excel(file, sheet_name=sheet_name)
            return df.to_dict(orient='records')
        except Exception as e:
            raise ValueError(f"Erro ao processar arquivo Excel: {str(e)}")

    def read_csv_file(self, file, delimiter=',', encoding='utf-8'):
        try:
            df = pd.read_csv(file, delimiter=delimiter, encoding=encoding)
            return df.to_dict(orient='records')
        except Exception as e:
            raise ValueError(f"Erro ao processar arquivo CSV: {str(e)}")

    def convert_data_types(self, data, type_mapping):
        if isinstance(data, list):
            return [self.convert_data_types(item, type_mapping) for item in data]

        result = data.copy()
        for key, type_name in type_mapping.items():
            if key in result and result[key] is not None:
                try:
                    if type_name == 'decimal':
                        if isinstance(result[key], str):
                            clean_value = result[key].replace('R$', '').replace('.', '').replace(',', '.')
                            result[key] = Decimal(clean_value)
                        else:
                            result[key] = Decimal(str(result[key]))
                    elif type_name == 'date':
                        if isinstance(result[key], str):
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                                try:
                                    result[key] = datetime.datetime.strptime(result[key], fmt).date()
                                    break
                                except ValueError:
                                    continue
                            if isinstance(result[key], str):
                                raise ValueError(f"Formato de data não reconhecido: {result[key]}")
                        elif isinstance(result[key], (int, float)):
                            result[key] = (datetime.datetime(1899, 12, 30) + datetime.timedelta(days=int(result[key]))).date()
                    elif type_name == 'datetime':
                        if isinstance(result[key], str):
                            for fmt in ['%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S']:
                                try:
                                    result[key] = datetime.datetime.strptime(result[key], fmt)
                                    break
                                except ValueError:
                                    continue
                            if isinstance(result[key], str):
                                raise ValueError(f"Formato de data e hora não reconhecido: {result[key]}")
                    elif type_name == 'boolean':
                        if isinstance(result[key], str):
                            result[key] = result[key].lower() in ['true', 'sim', 's', 'yes', 'y', '1']
                        else:
                            result[key] = bool(result[key])
                    elif type_name == 'integer':
                        if isinstance(result[key], str):
                            clean_value = ''.join(c for c in result[key] if c.isdigit() or c == '-')
                            result[key] = int(clean_value)
                        else:
                            result[key] = int(result[key])
                    elif type_name == 'float':
                        if isinstance(result[key], str):
                            clean_value = result[key].replace('R$', '').replace('.', '').replace(',', '.')
                            result[key] = float(clean_value)
                        else:
                            result[key] = float(result[key])
                    elif type_name == 'string':
                        result[key] = str(result[key])
                except Exception as e:
                    logger.error(f"Erro ao converter {key}: {e}")
        return result

    def validate_data(self, data, required_fields=None, allowed_values=None, min_max_values=None):
        if isinstance(data, list):
            all_valid = True
            all_errors = []
            for idx, item in enumerate(data):
                valid, errors = self.validate_data(item, required_fields, allowed_values, min_max_values)
                if not valid:
                    all_valid = False
                    for err in errors:
                        all_errors.append(f"Item {idx + 1}: {err}")
            return all_valid, all_errors

        errors = []
        if required_fields:
            for field in required_fields:
                if field not in data or data[field] is None or data[field] == '':
                    errors.append(f"Campo '{field}' é obrigatório")
        if allowed_values:
            for field, values in allowed_values.items():
                if field in data and data[field] is not None and data[field] != '' and data[field] not in values:
                    errors.append(f"Valor '{data[field]}' inválido para o campo '{field}'. Valores permitidos: {values}")
        if min_max_values:
            for field, limits in min_max_values.items():
                if field in data and data[field] is not None and data[field] != '':
                    if 'min' in limits and data[field] < limits['min']:
                        errors.append(f"Valor '{data[field]}' para o campo '{field}' é menor que o mínimo permitido ({limits['min']})")
                    if 'max' in limits and data[field] > limits['max']:
                        errors.append(f"Valor '{data[field]}' para o campo '{field}' é maior que o máximo permitido ({limits['max']})")
        return len(errors) == 0, errors

    def save_data_as_json(self, data, file_path):
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            class JSONEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, Decimal):
                        return float(obj)
                    if isinstance(obj, (datetime.date, datetime.datetime)):
                        return obj.isoformat()
                    if isinstance(obj, uuid.UUID):
                        return str(obj)
                    return super().default(obj)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, cls=JSONEncoder, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dados como JSON: {str(e)}")
            return False

    def load_data_from_json(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Erro ao carregar dados do arquivo JSON: {str(e)}")

    def process_file_upload(self, request, file_field='file', supported_types=None):
        try:
            if file_field not in request.FILES:
                raise ValueError(f"Nenhum arquivo enviado no campo '{file_field}'")
            file = request.FILES[file_field]
            _, ext = os.path.splitext(file.name)
            ext = ext.lower()
            if supported_types and ext not in supported_types:
                raise ValueError(f"Tipo de arquivo não suportado. Tipos suportados: {', '.join(supported_types)}")
            saved_path = self.save_file(file)
            if ext == '.json':
                data = self.read_json_file(file)
            elif ext in ('.xlsx', '.xls'):
                data = self.read_excel_file(file)
            elif ext == '.csv':
                data = self.read_csv_file(file)
            else:
                return None, saved_path
            return data, saved_path
        except Exception as e:
            if hasattr(request, 'user'):
                self.log_error(
                    request=request, action='file_upload',
                    message=f"Erro ao processar arquivo: {str(e)}",
                    data={'filename': request.FILES[file_field].name if file_field in request.FILES else None}
                )
            return None, None


class BaseApiView(LoggingMixin, FileProcessingMixin, APIView):
    """
    Classe base para APIs com logging, auditoria e processamento de arquivos.
    """
    pass
