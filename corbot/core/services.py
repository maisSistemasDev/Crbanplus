import json
import uuid
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog, ActionLog


# Classe personalizada de JSONEncoder para lidar com UUIDs e outros tipos não serializáveis
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # Converte UUID para string
            return str(obj)
        # Tenta converter outros tipos personalizados aqui, se necessário
        return super().default(obj)


# Função auxiliar para serializar dados para JSON
def serialize_for_json(data):
    if data is None:
        return None
    return json.loads(json.dumps(data, cls=CustomJSONEncoder))


class AuditService:
    """
    Serviço para registrar logs de auditoria.
    """
    @staticmethod
    def log_create(user, instance, data_after=None, ip_address=None, user_agent=None):
        """
        Registra a criação de um objeto.
        """
        content_type = ContentType.objects.get_for_model(instance)
        
        if data_after is None:
            # Se não for fornecido, tenta serializar o objeto
            if hasattr(instance, 'to_dict'):
                data_after = instance.to_dict()
            else:
                # Fallback simples para objetos sem método to_dict
                data_after = {
                    'id': instance.id,
                    'str': str(instance)
                }
        
        # Serializa os dados para garantir que são JSON serializáveis
        data_after = serialize_for_json(data_after)
        
        return AuditLog.objects.create(
            user=user,
            action=AuditLog.ACTION_CREATE,
            content_type=content_type,
            object_id=instance.id,
            data_after=data_after,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_update(user, instance, data_before=None, data_after=None, ip_address=None, user_agent=None):
        """
        Registra a atualização de um objeto.
        """
        content_type = ContentType.objects.get_for_model(instance)
        
        if data_before is None or data_after is None:
            # Se não for fornecido, tenta serializar o objeto
            if hasattr(instance, 'to_dict'):
                if data_after is None:
                    data_after = instance.to_dict()
                # Para data_before, precisaria ter sido capturado antes da atualização
            else:
                # Fallback simples para objetos sem método to_dict
                if data_after is None:
                    data_after = {
                        'id': instance.id,
                        'str': str(instance)
                    }
        
        # Serializa os dados para garantir que são JSON serializáveis
        data_before = serialize_for_json(data_before)
        data_after = serialize_for_json(data_after)
        
        return AuditLog.objects.create(
            user=user,
            action=AuditLog.ACTION_UPDATE,
            content_type=content_type,
            object_id=instance.id,
            data_before=data_before,
            data_after=data_after,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_delete(user, instance, data_before=None, ip_address=None, user_agent=None):
        """
        Registra a exclusão de um objeto.
        """
        content_type = ContentType.objects.get_for_model(instance)
        
        if data_before is None:
            # Se não for fornecido, tenta serializar o objeto
            if hasattr(instance, 'to_dict'):
                data_before = instance.to_dict()
            else:
                # Fallback simples para objetos sem método to_dict
                data_before = {
                    'id': instance.id,
                    'str': str(instance)
                }
        
        # Serializa os dados para garantir que são JSON serializáveis
        data_before = serialize_for_json(data_before)
        
        return AuditLog.objects.create(
            user=user,
            action=AuditLog.ACTION_DELETE,
            content_type=content_type,
            object_id=instance.id,
            data_before=data_before,
            ip_address=ip_address,
            user_agent=user_agent
        )


class LogService:
    """
    Serviço para registrar logs de ações.
    """
    @staticmethod
    def log(user, action, message, level=ActionLog.LEVEL_INFO, data=None, ip_address=None, user_agent=None):
        """
        Registra uma ação.
        """
        # Serializa os dados para garantir que são JSON serializáveis
        data = serialize_for_json(data)
        
        return ActionLog.objects.create(
            user=user,
            level=level,
            action=action,
            message=message,
            data=data,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def debug(user, action, message, data=None, ip_address=None, user_agent=None):
        """
        Registra uma ação de nível debug.
        """
        # Serializa os dados para garantir que são JSON serializáveis
        data = serialize_for_json(data)
        
        return LogService.log(
            user=user,
            action=action,
            message=message,
            level=ActionLog.LEVEL_DEBUG,
            data=data,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def info(user, action, message, data=None, ip_address=None, user_agent=None):
        """
        Registra uma ação de nível info.
        """
        # Serializa os dados para garantir que são JSON serializáveis
        data = serialize_for_json(data)
        
        return LogService.log(
            user=user,
            action=action,
            message=message,
            level=ActionLog.LEVEL_INFO,
            data=data,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def warning(user, action, message, data=None, ip_address=None, user_agent=None):
        """
        Registra uma ação de nível warning.
        """
        # Serializa os dados para garantir que são JSON serializáveis
        data = serialize_for_json(data)
        
        return LogService.log(
            user=user,
            action=action,
            message=message,
            level=ActionLog.LEVEL_WARNING,
            data=data,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def error(user, action, message, data=None, ip_address=None, user_agent=None):
        """
        Registra uma ação de nível error.
        """
        # Serializa os dados para garantir que são JSON serializáveis
        data = serialize_for_json(data)
        
        return LogService.log(
            user=user,
            action=action,
            message=message,
            level=ActionLog.LEVEL_ERROR,
            data=data,
            ip_address=ip_address,
            user_agent=user_agent
        ) 