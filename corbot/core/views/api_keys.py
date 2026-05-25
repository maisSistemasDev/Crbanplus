from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import APIKey
from core.permissions import IsPromotoraAdmin


class APIKeySerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'prefix', 'scopes', 'is_active',
            'expires_at', 'last_used_at', 'created_at', 'updated_at',
            'created_by', 'created_by_name', 'company', 'company_name',
            'is_expired',
        ]
        read_only_fields = [
            'id', 'prefix', 'last_used_at', 'created_at', 'updated_at',
            'created_by', 'created_by_name', 'company_name', 'is_expired',
        ]

    def get_created_by_name(self, obj):
        u = obj.created_by
        full = f'{u.first_name} {u.last_name}'.strip()
        return full or u.cpf

    def get_company_name(self, obj):
        return obj.company.name if obj.company else None

    def get_is_expired(self, obj):
        from django.utils import timezone
        if obj.expires_at:
            return obj.expires_at < timezone.now()
        return False

    def validate_scopes(self, value):
        valid = {s[0] for s in APIKey.SCOPE_CHOICES}
        invalid = set(value) - valid
        if invalid:
            raise serializers.ValidationError(f'Escopos inválidos: {", ".join(invalid)}')
        return list(set(value))


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer usado apenas na criação — expõe o full_key uma única vez."""

    class Meta:
        model = APIKey
        fields = ['id', 'name', 'scopes', 'expires_at', 'company']

    def validate_scopes(self, value):
        valid = {s[0] for s in APIKey.SCOPE_CHOICES}
        invalid = set(value) - valid
        if invalid:
            raise serializers.ValidationError(f'Escopos inválidos: {", ".join(invalid)}')
        if not value:
            raise serializers.ValidationError('Selecione ao menos um escopo.')
        return list(set(value))

    def create(self, validated_data):
        full_key, prefix, hashed_key = APIKey.generate_key()
        api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed_key,
            **validated_data,
        )
        # Armazena temporariamente para retornar ao chamador
        api_key._full_key = full_key
        return api_key


class APIKeyViewSet(ModelViewSet):
    """
    CRUD de Chaves de API.
    Apenas administradores da promotora podem acessar.
    """
    queryset = APIKey.objects.select_related('created_by', 'company').all()
    permission_classes = [IsPromotoraAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return APIKeyCreateSerializer
        return APIKeySerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        api_key = serializer.instance
        return Response(
            {
                **APIKeySerializer(api_key, context=self.get_serializer_context()).data,
                'key': api_key._full_key,
                'warning': 'Guarde esta chave agora. Ela não será exibida novamente.',
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        # Somente PATCH é permitido (apenas name, scopes, is_active, expires_at)
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='revoke')
    def revoke(self, request, pk=None):
        """Revoga (desativa) uma chave de API."""
        api_key = self.get_object()
        api_key.is_active = False
        api_key.save(update_fields=['is_active', 'updated_at'])
        return Response({'detail': 'Chave revogada com sucesso.'})

    @action(detail=False, methods=['get'], url_path='available-scopes')
    def available_scopes(self, request):
        """Retorna os escopos disponíveis."""
        scopes = [{'value': s[0], 'label': str(s[1])} for s in APIKey.SCOPE_CHOICES]
        return Response(scopes)
