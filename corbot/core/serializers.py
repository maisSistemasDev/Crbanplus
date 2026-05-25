from rest_framework import serializers
from .models import User, ExtraData, Company, UserPermission, PermissionTemplate
import secrets
import string


class CompanySerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo Company (Corban).
    """
    class Meta:
        model = Company
        fields = ['id', 'name', 'trading_name', 'person_type', 'document', 'logo', 'primary_color', 
                 'secondary_color', 'accent_color', 'settings', 'email', 'phone', 
                 'website', 'address', 'city', 'state', 'zip_code', 'is_active']
        read_only_fields = ['id']
        
    def form_fields(self, instance=None):
        """
        Retorna informações sobre os campos para construção de formulários no NextJS.
        """
        return [
            {'name': 'name', 'type': 'text', 'label': 'Nome', 'required': True},
            {'name': 'trading_name', 'type': 'text', 'label': 'Nome Fantasia', 'required': False},
            {'name': 'person_type', 'type': 'select', 'label': 'Tipo de Pessoa', 'required': True,
             'options': [{'value': 'PF', 'label': 'Pessoa Física'}, {'value': 'PJ', 'label': 'Pessoa Jurídica'}],
             'default': 'PJ'},
            {'name': 'document', 'type': 'text', 'label': 'CPF/CNPJ', 'required': True, 'mask': '99.999.999/9999-99'},
            {'name': 'logo', 'type': 'file', 'label': 'Logo', 'required': False, 'accept': 'image/*'},
            {'name': 'primary_color', 'type': 'color', 'label': 'Cor Primária', 'required': False},
            {'name': 'secondary_color', 'type': 'color', 'label': 'Cor Secundária', 'required': False},
            {'name': 'accent_color', 'type': 'color', 'label': 'Cor de Destaque', 'required': False},
            {'name': 'email', 'type': 'email', 'label': 'Email', 'required': False},
            {'name': 'phone', 'type': 'text', 'label': 'Telefone', 'required': False, 'mask': '(99) 99999-9999'},
            {'name': 'website', 'type': 'url', 'label': 'Website', 'required': False},
            {'name': 'address', 'type': 'text', 'label': 'Endereço', 'required': False},
            {'name': 'city', 'type': 'text', 'label': 'Cidade', 'required': False},
            {'name': 'state', 'type': 'text', 'label': 'Estado', 'required': False},
            {'name': 'zip_code', 'type': 'text', 'label': 'CEP', 'required': False, 'mask': '99999-999'},
            {'name': 'is_active', 'type': 'checkbox', 'label': 'Ativo', 'default': True},
        ]
    
    def create(self, validated_data):
        """
        Cria um corban.
        NOTA: O usuário empresa_admin deve ser criado separadamente com um CPF válido.
        O document da Company pode ser CPF (PF) ou CNPJ (PJ), mas o User.cpf sempre precisa de um CPF.
        """
        # Cria o corban
        company = Company.objects.create(**validated_data)
        
        # Log da criação
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'Corban criado: {company.name} (ID: {company.id}), Document: {company.document}, Tipo: {company.person_type}')
        
        return company


class ExtraDataSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo ExtraData.
    """
    class Meta:
        model = ExtraData
        fields = '__all__'
        
    def form_fields(self):
        """
        Retorna informações sobre os campos para construção de formulários no NextJS.
        """
        # Como ExtraData pode ter campos dinâmicos, retornamos apenas o campo básico
        return [
            {'name': 'user', 'type': 'select', 'label': 'Usuário', 'required': True, 'relation': 'User'},
            {'name': 'data', 'type': 'json', 'label': 'Dados Adicionais', 'required': False}
        ]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo User.
    """
    extra_data = ExtraDataSerializer(required=False)
    is_gerente = serializers.SerializerMethodField()
    is_lider = serializers.SerializerMethodField()
    is_vendedor = serializers.SerializerMethodField()
    is_empresa_admin = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'cpf', 'email', 'first_name', 'last_name', 'role',
                 'leader', 'company', 'company_name', 'is_active', 'extra_data',
                 'is_gerente', 'is_lider', 'is_vendedor', 'is_empresa_admin', 'password',
                 'certificado', 'matricula']
        read_only_fields = ['id']

    def get_is_gerente(self, obj):
        return obj.role == User.GERENTE
    
    def get_is_lider(self, obj):
        return obj.role == User.LIDER
    
    def get_is_vendedor(self, obj):
        return obj.role == User.VENDEDOR

    def get_is_empresa_admin(self, obj):
        return obj.role == User.EMPRESA_ADMIN
    
    def get_company_name(self, obj):
        if obj.company:
            return obj.company.name
        return None

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        
        return user

    def update(self, instance, validated_data):
        extra_data = validated_data.pop('extra_data', None)
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        
        if password:
            user.set_password(password)
            user.save()
            
        if extra_data and hasattr(instance, 'extra_data'):
            for attr, value in extra_data.items():
                setattr(instance.extra_data, attr, value)
            instance.extra_data.save()
        elif extra_data:
            ExtraData.objects.create(user=instance, **extra_data)
            
        return user
    
    def form_fields(self, instance=None):
        """
        Retorna informações sobre os campos para construção de formulários no NextJS.
        """
        if instance:
            return [
                {'name': 'cpf', 'type': 'text', 'label': 'CPF', 'required': True, 'mask': '999.999.999-99'},
                {'name': 'email', 'type': 'email', 'label': 'Email', 'required': True},
                {'name': 'first_name', 'type': 'text', 'label': 'Nome', 'required': True},
                {'name': 'last_name', 'type': 'text', 'label': 'Sobrenome', 'required': True},
                {'name': 'role', 'type': 'select', 'label': 'Função', 'required': True, 
                 'options': [{'value': role, 'label': role.upper()} for role, _ in User.ROLE_CHOICES]},
                {'name': 'company', 'type': 'select', 'label': 'Corban', 'required': True, 'relation': 'Company',
                 'options': [{'value': company.id, 'label': company.name} for company in Company.objects.filter(is_active=True)]},
                 {'name': 'password', 'type': 'password', 'label': 'Senha', 'required': True},
                {'name': 'certificado', 'type': 'text', 'label': 'Certificado', 'required': False},
                {'name': 'matricula', 'type': 'text', 'label': 'Matrícula', 'required': False, 'placeholder': 'Deixe em branco para usar o CPF'},           
                  {'name': 'pix_type', 'type': 'select', 'label': 'Tipo de PIX', 'required': False, 
                 'options': [{'value': pix_type, 'label': label} for pix_type, label in ExtraData.PIX_TYPE_CHOICES]},
                {'name': 'pix_key', 'type': 'text', 'label': 'Chave PIX', 'required': False},
                {'name': 'birth_date', 'type': 'date', 'label': 'Data de Nascimento', 'required': False},
                {'name': 'phone', 'type': 'text', 'label': 'Telefone', 'required': False, 'mask': '(99) 99999-9999'},
                {'name': 'rg', 'type': 'text', 'label': 'RG', 'required': False},
                {'name': 'rg_emission_date', 'type': 'date', 'label': 'Data de Emissão do RG', 'required': False},
                {'name': 'rg_emission_organ', 'type': 'text', 'label': 'Órgão Emissor do RG', 'required': False},
                {'name': 'is_active', 'type': 'checkbox', 'label': 'Ativo', 'default': True, 'value': True},
            ]
        else:
            return [
                {'name': 'cpf', 'type': 'text', 'label': 'CPF', 'required': True, 'mask': '999.999.999-99'},
                {'name': 'email', 'type': 'email', 'label': 'Email', 'required': True},
                {'name': 'first_name', 'type': 'text', 'label': 'Nome', 'required': True},
                {'name': 'last_name', 'type': 'text', 'label': 'Sobrenome', 'required': True},
            ]
        
    
    
class UserCreateSerializer(UserSerializer):
    """
    Serializador para criação de usuários.
    """
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['password']
        
    def form_fields(self, instance=None):
        """
        Retorna informações sobre os campos para construção de formulários no NextJS.
        """
        fields = super().form_fields(instance=instance)
        # Adiciona o campo de senha para criação
        fields.append({'name': 'password', 'type': 'password', 'label': 'Senha', 'required': True})
        return fields


class UserListSerializer(UserSerializer):
    """
    Serializador para listagem de usuários.
    """
    leader_name = serializers.SerializerMethodField()
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['leader_name']
    
    def get_leader_name(self, obj):
        if obj.leader:
            return f"{obj.leader.first_name} {obj.leader.last_name}".strip() or obj.leader.cpf
        return None 


class CreateManagerSerializer(serializers.ModelSerializer):
    """
    Serializer para criar um novo usuário com a role de Gerente.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ('cpf', 'email', 'first_name', 'last_name', 'password', 'company') # Adicione outros campos se necessário
        extra_kwargs = {
            'email': {'required': True},
        }

    def create(self, validated_data):
        validated_data['role'] = User.GERENTE
        user = User.objects.create_user(**validated_data) # Usa create_user para hashear a senha
        return user
        
    def form_fields(self):
        """
        Retorna informações sobre os campos para construção de formulários no NextJS.
        """
        return [
            {'name': 'cpf', 'type': 'text', 'label': 'CPF', 'required': True, 'mask': '999.999.999-99'},
            {'name': 'email', 'type': 'email', 'label': 'Email', 'required': True},
            {'name': 'first_name', 'type': 'text', 'label': 'Nome', 'required': True},
            {'name': 'last_name', 'type': 'text', 'label': 'Sobrenome', 'required': True},
            {'name': 'password', 'type': 'password', 'label': 'Senha', 'required': True},
            {'name': 'company', 'type': 'select', 'label': 'Empresa', 'required': True, 'relation': 'Company'}
        ] 


class UserPermissionSerializer(serializers.ModelSerializer):
    """
    Serializador para permissões de usuários.
    """
    class Meta:
        model = UserPermission
        fields = ['id', 'user', 'codename', 'name', 'category', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class PermissionTemplateSerializer(serializers.ModelSerializer):
    """
    Serializador para templates de permissões.
    """
    permission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PermissionTemplate
        fields = ['id', 'name', 'description', 'permissions', 'is_active', 'permission_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_permission_count(self, obj):
        return len(obj.permissions)


class InternalUserSerializer(serializers.ModelSerializer):
    """
    Serializador para usuários internos da promotora (Admin e Colaborador).
    """
    password = serializers.CharField(write_only=True, required=False)
    permissions = UserPermissionSerializer(source='custom_permissions', many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'cpf', 'email', 'first_name', 'last_name', 'role',
            'is_active', 'password', 'permissions', 'permission_count',
            'certificado', 'matricula', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'cpf': {'required': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': True},
        }
    
    def get_permission_count(self, obj):
        if obj.role == User.COLABORADOR:
            return obj.custom_permissions.count()
        return 0
    
    def validate_role(self, value):
        """Valida que o role seja apenas ADMIN ou COLABORADOR"""
        if value not in [User.ADMIN, User.COLABORADOR]:
            raise serializers.ValidationError(
                'Role inválido para usuário interno. Use "admin" ou "colaborador".'
            )
        return value
    
    def validate_cpf(self, value):
        """Valida CPF único para usuários internos"""
        import re
        cpf = re.sub(r'\D', '', value)
        if len(cpf) != 11:
            raise serializers.ValidationError('CPF deve ter 11 dígitos.')
        
        # Verifica se já existe outro usuário com este CPF
        if self.instance:
            if User.objects.filter(cpf=cpf).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError('Já existe um usuário com este CPF.')
        else:
            if User.objects.filter(cpf=cpf).exists():
                raise serializers.ValidationError('Já existe um usuário com este CPF.')
        
        return cpf
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        # Usuários internos não têm company vinculada
        validated_data['company'] = None
        
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            # Gera senha temporária se não fornecida
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            user.set_password(temp_password)
        
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance
    
    def form_fields(self, instance=None):
        """
        Retorna informações sobre os campos para construção de formulários no NextJS.
        """
        return [
            {'name': 'cpf', 'type': 'text', 'label': 'CPF', 'required': True, 'mask': '999.999.999-99'},
            {'name': 'email', 'type': 'email', 'label': 'Email', 'required': True},
            {'name': 'first_name', 'type': 'text', 'label': 'Nome', 'required': True},
            {'name': 'last_name', 'type': 'text', 'label': 'Sobrenome', 'required': True},
            {'name': 'role', 'type': 'select', 'label': 'Tipo de Usuário', 'required': True,
             'options': [
                 {'value': User.ADMIN, 'label': 'Administrador'},
                 {'value': User.COLABORADOR, 'label': 'Colaborador'}
             ]},
            {'name': 'password', 'type': 'password', 'label': 'Senha', 'required': not instance},
            {'name': 'certificado', 'type': 'text', 'label': 'Certificado', 'required': False},
            {'name': 'matricula', 'type': 'text', 'label': 'Matrícula', 'required': False},
            {'name': 'is_active', 'type': 'checkbox', 'label': 'Ativo', 'default': True},
        ]


class CollaboratorPermissionsSerializer(serializers.Serializer):
    """
    Serializador para gerenciar permissões de um colaborador.
    """
    user_id = serializers.IntegerField(required=True)
    permissions = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        required=True
    )
    
    def validate_user_id(self, value):
        """Valida que o usuário existe e é um colaborador"""
        try:
            user = User.objects.get(id=value)
            if user.role != User.COLABORADOR:
                raise serializers.ValidationError('O usuário deve ser um colaborador.')
        except User.DoesNotExist:
            raise serializers.ValidationError('Usuário não encontrado.')
        return value
    
    def save(self):
        """Atualiza as permissões do colaborador"""
        user_id = self.validated_data['user_id']
        permissions_data = self.validated_data['permissions']
        
        user = User.objects.get(id=user_id)
        
        # Remove permissões antigas
        user.custom_permissions.all().delete()
        
        # Adiciona novas permissões
        for perm_data in permissions_data:
            UserPermission.objects.create(
                user=user,
                codename=perm_data['codename'],
                name=perm_data['name'],
                category=perm_data.get('category', UserPermission.CATEGORY_SETTINGS),
                description=perm_data.get('description', '')
            )
        
        return user

