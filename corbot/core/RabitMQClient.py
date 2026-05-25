import pika
import json
import logging
import threading
import time
from typing import Callable, Dict, Any
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)

class RabbitMQClient:
    """Cliente para gerenciar conexões e operações com RabbitMQ"""
    
    def __init__(self, host='localhost', port=5672, username='guest', password='guest', user_id=None):
        """
        Inicializar cliente RabbitMQ
        
        Args:
            host: Host do RabbitMQ
            port: Porta do RabbitMQ
            username: Nome de usuário
            password: Senha
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.user_id = user_id
        self.connection = None
        self.channel = None
        self.callbacks = {}
        self.consumer_thread = None
        self.is_consuming = False
        
        # Configurar exchanges e filas
        self.exchanges = {
            'chat': 'chat_exchange',
            'rooms': 'rooms_exchange',
            'notifications': 'notifications_exchange'
        }
        
        self.queues = {
            'chat_messages': 'chat_messages_queue',
            'room_messages': 'room_messages_queue',
            'user_notifications': 'user_notifications_queue',
            'system_events': 'system_events_queue'
        }
        
    def connect(self):
        """Conectar ao RabbitMQ"""
        try:
            # Configurar credenciais
            credentials = pika.PlainCredentials(self.username, self.password)
            
            # Parâmetros de conexão
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            # Estabelecer conexão
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Configurar exchanges e filas
            self._setup_exchanges_and_queues()
            
            logger.info(f"✅ Conectado ao RabbitMQ em {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao RabbitMQ: {e}")
            return False
    
    def _setup_exchanges_and_queues(self):
        """Configurar exchanges e filas necessárias"""
        try:
            # Declarar exchanges
            for exchange_name in self.exchanges.values():
                self.channel.exchange_declare(
                    exchange=exchange_name,
                    exchange_type='topic',
                    durable=True
                )
            
            # Declarar filas
            for queue_name in self.queues.values():
                self.channel.queue_declare(
                    queue=queue_name,
                    durable=True
                )
            
            # Bind filas aos exchanges
            self.channel.queue_bind(
                exchange=self.exchanges['chat'],
                queue=self.queues['chat_messages'],
                routing_key='chat.message.*'
            )
            
            self.channel.queue_bind(
                exchange=self.exchanges['rooms'],
                queue=self.queues['room_messages'],
                routing_key='room.message.*'
            )
            
            self.channel.queue_bind(
                exchange=self.exchanges['notifications'],
                queue=self.queues['user_notifications'],
                routing_key='user.*'
            )
            
            self.channel.queue_bind(
                exchange=self.exchanges['notifications'],
                queue=self.queues['system_events'],
                routing_key='system.*'
            )
            
            logger.info("✅ Exchanges e filas configuradas com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar exchanges e filas: {e}")
            raise
    
    def publish_message(self, exchange: str, routing_key: str, message: Dict[Any, Any], user_id: str = None):
        """
        Publicar mensagem no RabbitMQ
        
        Args:
            exchange: Nome do exchange
            routing_key: Chave de roteamento
            message: Dados da mensagem
        """
        try:
            if not self.channel:
                logger.error("❌ Não conectado ao RabbitMQ")
                return False
            
            # Converter mensagem para JSON
            message_body = json.dumps(message, ensure_ascii=False)
            
            # Publicar mensagem
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Tornar mensagem persistente
                    timestamp=int(time.time()),
                    user_id=self.user_id
                )
            )
            
            logger.info(f"📤 Mensagem publicada: {exchange}/{routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao publicar mensagem: {e}")
            return False
    
    def publish_chat_message(self, message_data: Dict[Any, Any]):
        """Publicar mensagem de chat geral"""
        return self.publish_message(
            exchange=self.exchanges['chat'],
            routing_key='chat.message.general',
            message=message_data
        )
    
    def publish_room_message(self, room: str, message_data: Dict[Any, Any]):
        """Publicar mensagem de sala"""
        return self.publish_message(
            exchange=self.exchanges['rooms'],
            routing_key=f'room.message.{room}',
            message=message_data
        )
    
    def publish_user_notification(self, event_type: str, data: Dict[Any, Any]):
        """Publicar notificação de usuário"""
        return self.publish_message(
            exchange=self.exchanges['notifications'],
            routing_key=f'user.{event_type}',
            message=data
        )
    
    def publish_system_event(self, event_type: str, data: Dict[Any, Any]):
        """Publicar evento do sistema"""
        return self.publish_message(
            exchange=self.exchanges['notifications'],
            routing_key=f'system.{event_type}',
            message=data
        )
    
    def add_callback(self, queue: str, callback: Callable):
        """
        Adicionar callback para processar mensagens de uma fila
        
        Args:
            queue: Nome da fila
            callback: Função callback
        """
        self.callbacks[queue] = callback
    
    def _process_message(self, ch, method, properties, body):
        """Processar mensagem recebida"""
        try:
            queue_name = method.routing_key
            message = json.loads(body.decode('utf-8'))
            
            # Encontrar callback apropriado
            callback = None
            for queue, cb in self.callbacks.items():
                if queue in method.routing_key or queue == method.routing_key:
                    callback = cb
                    break
            
            if callback:
                callback(message, method.routing_key)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"📥 Mensagem processada: {method.routing_key}")
            else:
                logger.warning(f"⚠️ Nenhum callback encontrado para: {method.routing_key}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start_consuming(self):
        """Iniciar consumo de mensagens"""
        try:
            if not self.channel:
                logger.error("❌ Não conectado ao RabbitMQ")
                return False
            
            # Configurar QoS
            self.channel.basic_qos(prefetch_count=10)
            
            # Configurar consumers para todas as filas
            for queue_name in self.queues.values():
                self.channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=self._process_message
                )
            
            self.is_consuming = True
            logger.info("🔄 Iniciando consumo de mensagens...")
            
            # Iniciar consumo em thread separada
            self.consumer_thread = threading.Thread(
                target=self._consume_messages,
                daemon=True
            )
            self.consumer_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar consumo: {e}")
            return False
    
    def _consume_messages(self):
        """Loop de consumo de mensagens"""
        try:
            while self.is_consuming:
                self.connection.process_data_events(time_limit=1)
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"❌ Erro no loop de consumo: {e}")
    
    def stop_consuming(self):
        """Parar consumo de mensagens"""
        try:
            self.is_consuming = False
            if self.channel:
                self.channel.stop_consuming()
            if self.consumer_thread:
                self.consumer_thread.join(timeout=5)
            logger.info("🛑 Consumo de mensagens parado")
        except Exception as e:
            logger.error(f"❌ Erro ao parar consumo: {e}")
    
    def disconnect(self):
        """Desconectar do RabbitMQ"""
        try:
            self.stop_consuming()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("👋 Desconectado do RabbitMQ")
        except Exception as e:
            logger.error(f"❌ Erro ao desconectar: {e}")
    
    def is_connected(self):
        """Verificar se está conectado"""
        return (self.connection and 
                not self.connection.is_closed and 
                self.channel and 
                not self.channel.is_closed) 