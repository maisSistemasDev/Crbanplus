import hashlib
import re
import secrets
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class TimeStampedModel(models.Model):
    """
    Modelo abstrato que fornece campos de data de criação e atualização.
    """
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('atualizado em'), auto_now=True)
    
    class Meta:
        abstract = True


class Company(TimeStampedModel):
    """
    Modelo para representar as empresas (corbans) que receberão o whitelabel.
    """
    PERSON_TYPE_PF = 'PF'
    PERSON_TYPE_PJ = 'PJ'
    
    PERSON_TYPE_CHOICES = [
        (PERSON_TYPE_PF, _('Pessoa Física')),
        (PERSON_TYPE_PJ, _('Pessoa Jurídica')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nome'), max_length=255)
    trading_name = models.CharField(_('nome fantasia'), max_length=255, blank=True, null=True)
    person_type = models.CharField(_('tipo de pessoa'), max_length=2, choices=PERSON_TYPE_CHOICES, default=PERSON_TYPE_PJ)
    document = models.CharField(_('CPF/CNPJ'), max_length=18, unique=True)
    logo = models.ImageField(_('logo'), upload_to='company_logos/', blank=True, null=True)
    
    # Configurações de personalização
    primary_color = models.CharField(_('cor primária'), max_length=7, default='#3498db')
    secondary_color = models.CharField(_('cor secundária'), max_length=7, default='#2c3e50')
    accent_color = models.CharField(_('cor de destaque'), max_length=7, default='#e74c3c')
    
    # Configurações adicionais
    settings = models.JSONField(_('configurações'), default=dict, blank=True)
    
    # Dados de contato
    email = models.EmailField(_('email'), blank=True, null=True)
    phone = models.CharField(_('telefone'), max_length=20, blank=True, null=True)
    website = models.URLField(_('website'), blank=True, null=True)
    
    # Endereço
    address = models.CharField(_('endereço'), max_length=255, blank=True, null=True)
    city = models.CharField(_('cidade'), max_length=100, blank=True, null=True)
    state = models.CharField(_('estado'), max_length=2, blank=True, null=True)
    zip_code = models.CharField(_('CEP'), max_length=10, blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(_('ativo'), default=True)
    is_promotora = models.BooleanField(_('é promotora'), default=False, help_text=_('Marca esta empresa como a promotora principal do sistema'))
    
    class Meta:
        verbose_name = _('corban')
        verbose_name_plural = _('corbans')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Valida o documento baseado no tipo de pessoa."""
        from django.core.exceptions import ValidationError
        if self.document:
            # Remove formatação
            doc = re.sub(r'\D', '', self.document)
            
            if self.person_type == self.PERSON_TYPE_PF:
                # CPF deve ter 11 dígitos
                if len(doc) != 11:
                    raise ValidationError({'document': _('CPF deve ter 11 dígitos')})
            elif self.person_type == self.PERSON_TYPE_PJ:
                # CNPJ deve ter 14 dígitos
                if len(doc) != 14:
                    raise ValidationError({'document': _('CNPJ deve ter 14 dígitos')})
    
    def save(self, *args, **kwargs):
        """Normaliza o documento antes de salvar."""
        if self.document:
            self.document = re.sub(r'\D', '', self.document)
        self.full_clean()
        super().save(*args, **kwargs)


class UserManager(BaseUserManager):
    """
    Gerenciador de usuários personalizado para o modelo User.
    """
    def create_user(self, cpf, password=None, **extra_fields):
        """
        Cria e salva um usuário com o CPF e senha fornecidos.
        """
        if not cpf:
            raise ValueError(_('O CPF é obrigatório'))

        cpf = re.sub(r'\D', '', cpf)
        user = self.model(cpf=cpf, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, cpf, password=None, **extra_fields):
        """
        Cria e salva um superusuário com o CPF e senha fornecidos.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superusuário deve ter is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superusuário deve ter is_superuser=True.'))
        return self.create_user(cpf, password, **extra_fields)


class User(AbstractUser):
    """
    Modelo de usuário personalizado que usa CPF como identificador único.
    """
    # Definição de papéis - Promotora (usuários internos)
    ADMIN = 'admin'
    COLABORADOR = 'colaborador'
    
    # Definição de papéis - Corbans (empresas parceiras)
    EMPRESA_ADMIN = 'empresa_admin'
    GERENTE = 'gerente'
    LIDER = 'lider'
    VENDEDOR = 'vendedor'

    ROLE_CHOICES = (
        # Roles da Promotora
        (ADMIN, _('Administrador da Promotora')),
        (COLABORADOR, _('Colaborador da Promotora')),
        # Roles dos Corbans
        (EMPRESA_ADMIN, _('Administrador do Corban')),
        (GERENTE, _('Gerente')),
        (LIDER, _('Líder')),
        (VENDEDOR, _('Vendedor')),
    )
    
    username = None
    email = models.EmailField(_('endereço de email'), unique=True)
    cpf = models.CharField(_('CPF/CNPJ'), max_length=14, unique=True, help_text=_('CPF ou CNPJ sem formatação'))
    role = models.CharField(_('papel'), max_length=20, choices=ROLE_CHOICES, default=VENDEDOR)
    leader = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='team_members', verbose_name=_('líder'))
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users', 
                               verbose_name=_('corban'), null=True, blank=True)
    
    # Campos adicionais
    certificado = models.CharField(_('certificado'), max_length=100, blank=True, null=True)
    matricula = models.CharField(_('matrícula'), max_length=50, blank=True, null=True)
    
    USERNAME_FIELD = 'cpf'
    REQUIRED_FIELDS = ['email']
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('usuário')
        verbose_name_plural = _('usuários')
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'matricula'],
                name='unique_matricula_per_company',
                condition=models.Q(matricula__isnull=False)
            )
        ]
    
    def __str__(self):
        return self.cpf

    def save(self, *args, **kwargs):
        if self.cpf:
            self.cpf = re.sub(r'\D', '', self.cpf)
        
        # Se matrícula não informada, usar CPF como default
        if not self.matricula:
            self.matricula = self.cpf
        
        super().save(*args, **kwargs)
    
    @property
    def is_empresa_admin(self):
        return self.role == self.EMPRESA_ADMIN

    @property
    def is_gerente(self):
        return self.role == self.GERENTE
    
    @property
    def is_lider(self):
        return self.role == self.LIDER
    
    @property
    def is_vendedor(self):
        return self.role == self.VENDEDOR
    
    @property
    def is_admin(self):
        return self.role == self.ADMIN
    
    @property
    def is_colaborador(self):
        return self.role == self.COLABORADOR
    
    @property
    def is_promotora_user(self):
        """Verifica se o usuário é da promotora (ADMIN ou COLABORADOR)"""
        return self.role in [self.ADMIN, self.COLABORADOR]
    
    @property
    def is_corban_user(self):
        """Verifica se o usuário é de um corban"""
        return self.role in [self.EMPRESA_ADMIN, self.GERENTE, self.LIDER, self.VENDEDOR]
    
    def has_permission(self, permission_codename):
        """Verifica se o usuário tem uma permissão específica"""
        # Admin da promotora tem todas as permissões
        if self.role == self.ADMIN:
            return True
        
        # Colaboradores precisam ter a permissão explícita
        if self.role == self.COLABORADOR:
            return self.custom_permissions.filter(codename=permission_codename).exists()
        
        # Outros usuários não usam o sistema de permissões (por enquanto)
        return False


class UserPermission(TimeStampedModel):
    """
    Modelo para controlar permissões granulares de colaboradores da promotora.
    """
    # Categorias de permissões
    CATEGORY_CORBANS = 'corbans'
    CATEGORY_USERS = 'users'
    CATEGORY_PROPOSALS = 'proposals'
    CATEGORY_PAYMENTS = 'payments'
    CATEGORY_REPORTS = 'reports'
    CATEGORY_SETTINGS = 'settings'
    
    CATEGORY_CHOICES = [
        (CATEGORY_CORBANS, _('Gestão de Corbans')),
        (CATEGORY_USERS, _('Gestão de Usuários')),
        (CATEGORY_PROPOSALS, _('Gestão de Propostas')),
        (CATEGORY_PAYMENTS, _('Gestão de Pagamentos')),
        (CATEGORY_REPORTS, _('Relatórios')),
        (CATEGORY_SETTINGS, _('Configurações')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_permissions',
        verbose_name=_('usuário'),
        limit_choices_to={'role': User.COLABORADOR}
    )
    codename = models.CharField(_('código da permissão'), max_length=100)
    name = models.CharField(_('nome da permissão'), max_length=255)
    category = models.CharField(_('categoria'), max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(_('descrição'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('permissão de usuário')
        verbose_name_plural = _('permissões de usuários')
        unique_together = ['user', 'codename']
        ordering = ['category', 'codename']
    
    def __str__(self):
        return f'{self.user.cpf} - {self.name}'


class PermissionTemplate(TimeStampedModel):
    """
    Modelo para criar templates de permissões reutilizáveis.
    """
    name = models.CharField(_('nome'), max_length=100, unique=True)
    description = models.TextField(_('descrição'), blank=True, null=True)
    permissions = models.JSONField(
        _('permissões'),
        default=list,
        help_text=_('Lista de codenames de permissões incluídas neste template')
    )
    is_active = models.BooleanField(_('ativo'), default=True)
    
    class Meta:
        verbose_name = _('template de permissões')
        verbose_name_plural = _('templates de permissões')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ExtraData(TimeStampedModel):
    """
    Modelo para armazenar dados adicionais do usuário.
    """
    PIX_TYPE_ALEATORIA = 'CHAVE_ALEATORIA'
    PIX_TYPE_EMAIL = 'EMAIL'
    PIX_TYPE_PHONE = 'CELULAR'
    PIX_TYPE_CPF = 'CPF'
    PIX_TYPE_CNPJ = 'CNPJ'
    
    PIX_TYPE_CHOICES = [
        (PIX_TYPE_ALEATORIA, _('Chave Aleatória')),
        (PIX_TYPE_EMAIL, _('Email')),
        (PIX_TYPE_PHONE, _('Celular')),
        (PIX_TYPE_CPF, _('CPF')),
        (PIX_TYPE_CNPJ, _('CNPJ')),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='extra_data')
    rg = models.CharField(_('RG'), max_length=20, blank=True, null=True)
    rg_emission_date = models.DateField(_('data de emissão do RG'), blank=True, null=True)
    rg_emission_organ = models.CharField(_('órgão emissor do RG'), max_length=20, blank=True, null=True)
    birth_date = models.DateField(_('data de nascimento'), blank=True, null=True)
    phone = models.CharField(_('telefone'), max_length=20, blank=True, null=True)
    pix_key = models.CharField(_('chave PIX'), max_length=255, blank=True, null=True)
    pix_type = models.CharField(_('tipo de PIX'), max_length=255, choices=PIX_TYPE_CHOICES, blank=True, null=True)
    class Meta:
        verbose_name = _('dados adicionais')
        verbose_name_plural = _('dados adicionais')


class AuditLog(TimeStampedModel):
    """
    Modelo para registrar alterações nos dados.
    """
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    
    ACTION_CHOICES = (
        (ACTION_CREATE, _('Criação')),
        (ACTION_UPDATE, _('Atualização')),
        (ACTION_DELETE, _('Exclusão')),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(_('ação'), max_length=10, choices=ACTION_CHOICES)
    
    # Campos para o objeto alterado (Generic Foreign Key)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(_('ID do objeto'), max_length=50)  # Alterado para CharField para suportar UUIDs
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Dados antes e depois da alteração
    data_before = models.JSONField(_('dados antes'), null=True, blank=True)
    data_after = models.JSONField(_('dados depois'), null=True, blank=True)
    
    # Informações adicionais
    ip_address = models.GenericIPAddressField(_('endereço IP'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('log de auditoria')
        verbose_name_plural = _('logs de auditoria')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.content_type} - {self.object_id}"


class ActionLog(TimeStampedModel):
    """
    Modelo para registrar logs de ações nas views.
    """
    LEVEL_DEBUG = 'debug'
    LEVEL_INFO = 'info'
    LEVEL_WARNING = 'warning'
    LEVEL_ERROR = 'error'
    
    LEVEL_CHOICES = (
        (LEVEL_DEBUG, _('Debug')),
        (LEVEL_INFO, _('Informação')),
        (LEVEL_WARNING, _('Aviso')),
        (LEVEL_ERROR, _('Erro')),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='action_logs')
    level = models.CharField(_('nível'), max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    action = models.CharField(_('ação'), max_length=255)
    message = models.TextField(_('mensagem'))
    
    # Dados adicionais
    data = models.JSONField(_('dados'), null=True, blank=True)
    ip_address = models.GenericIPAddressField(_('endereço IP'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('log de ação')
        verbose_name_plural = _('logs de ação')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_level_display()} - {self.action}"


class ConnectorLog(TimeStampedModel):
    """
    Modelo para registrar logs de conexões.
    """
    connector = models.CharField(_('conector'), max_length=255)
    status = models.CharField(_('status'), max_length=255)
    response = models.JSONField(_('resposta'), null=True, blank=True)
    error = models.TextField(_('erro'), null=True, blank=True)


class ImportJob(TimeStampedModel):
    """
    Rastreia o progresso de importações em lote via CSV/XLSX.
    """
    ENTITY_VENDEDOR = 'vendedor'
    ENTITY_LIDER = 'lider'
    ENTITY_GERENTE = 'gerente'
    ENTITY_CORBAN = 'corban'
    ENTITY_BANK_ACCESS = 'bank_access'
    ENTITY_BANK = 'bank'

    ENTITY_CHOICES = [
        (ENTITY_VENDEDOR, _('Vendedor')),
        (ENTITY_LIDER, _('Líder')),
        (ENTITY_GERENTE, _('Gerente')),
        (ENTITY_CORBAN, _('Corban')),
        (ENTITY_BANK_ACCESS, _('Acesso Bancário')),
        (ENTITY_BANK, _('Banco')),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Aguardando')),
        (STATUS_PROCESSING, _('Processando')),
        (STATUS_DONE, _('Concluído')),
        (STATUS_FAILED, _('Falhou')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(_('tipo'), max_length=20, choices=ENTITY_CHOICES)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_rows = models.IntegerField(_('total de linhas'), default=0)
    processed_rows = models.IntegerField(_('linhas processadas'), default=0)
    created_count = models.IntegerField(_('criados'), default=0)
    error_count = models.IntegerField(_('erros'), default=0)
    errors = models.JSONField(_('detalhes de erros'), default=list)
    file_path = models.CharField(_('caminho do arquivo'), max_length=500, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='import_jobs',
        verbose_name=_('criado por'),
    )

    class Meta:
        verbose_name = _('job de importação')
        verbose_name_plural = _('jobs de importação')
        ordering = ['-created_at']

    def __str__(self):
        return f'ImportJob({self.entity_type}, {self.status}, {self.id})'

    @property
    def progress_pct(self):
        if not self.total_rows:
            return 0
        return round(self.processed_rows / self.total_rows * 100)


class SystemSettings(TimeStampedModel):
    """
    Configurações globais do sistema (singleton).
    """
    singleton = models.BooleanField(default=True, unique=True, editable=False)
    corbanpay_base_url = models.URLField(_('URL base CorbanPay'), blank=True, null=True)
    corbanpay_api_key = models.CharField(_('API key CorbanPay'), max_length=255, blank=True, null=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='updated_system_settings',
        verbose_name=_('atualizado por'),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('configuração do sistema')
        verbose_name_plural = _('configurações do sistema')

    def __str__(self):
        return 'Configurações do Sistema'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(singleton=True)
        return obj

    @property
    def masked_corbanpay_api_key(self):
        if not self.corbanpay_api_key:
            return ''
        if len(self.corbanpay_api_key) <= 8:
            return '*' * len(self.corbanpay_api_key)
        return f"{self.corbanpay_api_key[:4]}{'*' * (len(self.corbanpay_api_key) - 8)}{self.corbanpay_api_key[-4:]}"


class APIKey(TimeStampedModel):
    """
    Chaves de API para integração de terceiros.
    Apenas administradores da promotora podem criar/revogar chaves.
    O valor completo da chave é exibido UMA única vez no momento da criação.
    """

    SCOPE_CHOICES = [
        ('users:read', _('Usuários - Leitura')),
        ('users:write', _('Usuários - Escrita')),
        ('companies:read', _('Corbans - Leitura')),
        ('companies:write', _('Corbans - Escrita')),
        ('banks:read', _('Bancos - Leitura')),
        ('banks:write', _('Bancos - Escrita')),
        ('tables:read', _('Tabelas - Leitura')),
        ('tables:write', _('Tabelas - Escrita')),
        ('agreements:read', _('Convênios - Leitura')),
        ('agreements:write', _('Convênios - Escrita')),
        ('proposals:read', _('Propostas - Leitura')),
        ('proposals:write', _('Propostas - Escrita')),
        ('commissions:read', _('Comissões - Leitura')),
        ('commissions:write', _('Comissões - Escrita')),
        ('payments:read', _('Pagamentos - Leitura')),
        ('payments:write', _('Pagamentos - Escrita')),
        ('bank_access:read', _('Acessos Bancários - Leitura')),
        ('bank_access:write', _('Acessos Bancários - Escrita')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nome'), max_length=100)
    prefix = models.CharField(_('prefixo'), max_length=12, unique=True, editable=False)
    hashed_key = models.CharField(_('chave hash'), max_length=64, editable=False)
    scopes = models.JSONField(_('escopos'), default=list)
    is_active = models.BooleanField(_('ativo'), default=True)
    expires_at = models.DateTimeField(_('expira em'), null=True, blank=True)
    last_used_at = models.DateTimeField(_('último uso'), null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='api_keys', verbose_name=_('criado por')
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=True,
        related_name='api_keys', verbose_name=_('corban')
    )

    class Meta:
        verbose_name = _('chave de API')
        verbose_name_plural = _('chaves de API')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.prefix}***)'

    @classmethod
    def generate_key(cls):
        """Gera uma nova chave. Retorna (full_key, prefix, hashed_key)."""
        raw = secrets.token_hex(32)          # 64 hex chars
        prefix = 'crb_' + raw[:8]            # 12 chars: crb_xxxxxxxx
        full_key = 'crb_' + raw              # 68 chars total
        hashed = hashlib.sha256(full_key.encode()).hexdigest()
        return full_key, prefix, hashed

    @classmethod
    def verify_key(cls, key: str):
        """Verifica a chave e retorna a instância APIKey ou None."""
        if not key or not key.startswith('crb_') or len(key) < 12:
            return None
        prefix = key[:12]
        hashed = hashlib.sha256(key.encode()).hexdigest()
        try:
            api_key = cls.objects.select_related('created_by', 'company').get(
                prefix=prefix, hashed_key=hashed, is_active=True
            )
            if api_key.expires_at and api_key.expires_at < timezone.now():
                return None
            return api_key
        except cls.DoesNotExist:
            return None


class PushSubscription(models.Model):
    """
    Armazena subscriptions de Web Push por dispositivo/usuário.
    Cada dispositivo tem um endpoint único.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        verbose_name=_('usuário'),
    )
    endpoint = models.TextField(_('endpoint'), unique=True)
    p256dh = models.TextField(_('chave p256dh'))
    auth = models.TextField(_('chave auth'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('subscription de push')
        verbose_name_plural = _('subscriptions de push')
        ordering = ['-created_at']

    def __str__(self):
        return f'PushSubscription({self.user_id}, {self.endpoint[:40]}...)'
