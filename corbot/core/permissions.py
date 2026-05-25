from rest_framework import permissions


class IsGerente(permissions.BasePermission):
    """
    Permissão que permite acesso apenas a usuários com papel de Gerente.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'gerente'


class IsLider(permissions.BasePermission):
    """
    Permissão que permite acesso apenas a usuários com papel de Líder.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'lider'


class IsGerenteOrLider(permissions.BasePermission):
    """
    Permissão que permite acesso a usuários com papel de Gerente ou Líder.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_gerente or request.user.is_lider)


class IsOwnerOrLeader(permissions.BasePermission):
    """
    Permissão que permite acesso ao proprietário do objeto ou ao seu líder.
    """
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user or obj.user.leader == request.user
        if hasattr(obj, 'leader'):
            return obj == request.user or obj.leader == request.user
        return False


class IsAdmin(permissions.BasePermission):
    """
    Permissão que permite acesso apenas a Admin (promotora).
    Admin da promotora tem role='admin' e company=None.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == 'admin' and 
            request.user.company is None
        )


class IsPromotoraAdmin(permissions.BasePermission):
    """
    Permissão que permite acesso apenas a Admin da promotora.
    Alias para IsAdmin para clareza semântica.
    """
    def has_permission(self, request, view):
        from .models import User
        return (
            request.user.is_authenticated and 
            request.user.role == User.ADMIN and 
            request.user.company is None
        )


class IsPromotoraUser(permissions.BasePermission):
    """
    Permissão que permite acesso a usuários internos da promotora (Admin ou Colaborador).
    """
    def has_permission(self, request, view):
        from .models import User
        return (
            request.user.is_authenticated and 
            request.user.role in [User.ADMIN, User.COLABORADOR] and
            request.user.company is None
        )


class HasCollaboratorPermission(permissions.BasePermission):
    """
    Permissão que verifica se o colaborador tem uma permissão específica.
    A permissão necessária deve ser definida no atributo 'required_permission' da view.
    """
    def has_permission(self, request, view):
        from .models import User
        
        if not request.user.is_authenticated:
            return False
        
        # Admin da promotora sempre tem acesso
        if request.user.role == User.ADMIN and request.user.company is None:
            return True
        
        # Colaboradores precisam ter a permissão específica
        if request.user.role == User.COLABORADOR and request.user.company is None:
            required_perm = getattr(view, 'required_permission', None)
            if required_perm:
                return request.user.has_permission(required_perm)
        
        return False


class IsEmpresaAdmin(permissions.BasePermission):
    """
    Permissão que permite acesso apenas a Administrador do Corban.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'empresa_admin'


class IsAdminOrEmpresaAdmin(permissions.BasePermission):
    """
    Permissão que permite acesso a Admin (promotora) ou Administrador do Corban.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin', 'empresa_admin')


class IsAdminOrGerente(permissions.BasePermission):
    """
    Permissão que permite acesso a Admin (promotora), Admin do Corban ou Gerente.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin', 'empresa_admin', 'gerente')


class IsAdminOrGerenteOrLider(permissions.BasePermission):
    """
    Permissão que permite acesso a Admin (promotora), Admin do Corban, Gerente ou Líder.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin', 'empresa_admin', 'gerente', 'lider')
