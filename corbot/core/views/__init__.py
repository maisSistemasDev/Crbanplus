"""
Imports de todas as views para manter compatibilidade com código existente.

Atenção: Este arquivo é gerado automaticamente para importar todas as views
de módulos específicos. Qualquer alteração manual pode ser sobrescrita.
"""

# Importações de views de usuario
from .usuario import (
    UserListCreateView,
    UserDetailView,
    CreateManagerView,
    CurrentUserView
)

# Importações de views de vendedor
from .vendedor import (
    VendedoresListView,
    VendedorDetailView
)

# Importações de views de lider
from .lider import (
    LideresCreateListView,
    ChangeLeaderView,
    BatchChangeLeaderView
)

# Importações de views de empresa
from .empresa import (
    CompanyListCreateView,
    CompanyDetailView
)


# Importações de views de campos de formulário
from .form_fields import (
    UserFormFieldsView,
    UserCreateFormFieldsView,
    CompanyFormFieldsView,
    ExtraDataFormFieldsView,
    CreateManagerFormFieldsView,
)

# Importações de views de setup
from .setup import (
    SetupStatusView,
    SetupView
)

# Expor todas as views para manter compatibilidade com importações existentes
__all__ = [
    # Views de usuário
    'UserListCreateView', 'UserDetailView', 'VendedoresListView', 'VendedorDetailView',
    'CreateManagerView', 'CurrentUserView',

    # Views de líder
    'LideresCreateListView', 'ChangeLeaderView', 'BatchChangeLeaderView',

    # Views de empresa
    'CompanyListCreateView', 'CompanyDetailView',

    # Views de campos de formulário
    'UserFormFieldsView', 'UserCreateFormFieldsView', 'CompanyFormFieldsView',
    'ExtraDataFormFieldsView', 'CreateManagerFormFieldsView',

    # Views de setup
    'SetupStatusView', 'SetupView',
] 