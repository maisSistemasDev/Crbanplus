"""
Endpoints de autenticação com seleção de perfil (vendedor vs corban).
"""
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.auth_profiles import find_users_for_login, serialize_login_profile


def _issue_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class TokenObtainPairView(APIView):
    """
    POST /core/token/
    Body: { cpf, password }

    Um perfil → { access, refresh }
    Vários perfis → { requires_profile_selection, profiles }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        cpf = request.data.get('cpf') or request.data.get('username')
        password = request.data.get('password')

        if not cpf or not password:
            return Response(
                {'detail': 'CPF/CNPJ e senha são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = find_users_for_login(cpf, password)
        if not users:
            return Response(
                {'detail': 'Credenciais inválidas.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if len(users) == 1:
            return Response(_issue_tokens(users[0]))

        profiles = [serialize_login_profile(u) for u in users]
        return Response({
            'requires_profile_selection': True,
            'profiles': profiles,
        })


class TokenSelectProfileSerializer(serializers.Serializer):
    cpf = serializers.CharField()
    password = serializers.CharField(write_only=True)
    user_id = serializers.IntegerField()


class TokenSelectProfileView(APIView):
    """
    POST /core/token/select-profile/
    Body: { cpf, password, user_id }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenSelectProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cpf = serializer.validated_data['cpf']
        password = serializer.validated_data['password']
        user_id = serializer.validated_data['user_id']

        users = find_users_for_login(cpf, password)
        user = next((u for u in users if u.id == user_id), None)
        if not user:
            return Response(
                {'detail': 'Perfil inválido ou credenciais incorretas.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(_issue_tokens(user))
