"""
Imports de todas as views para manter compatibilidade com código existente.
"""

from .comission_group import (
    CommissionGroupListCreateView,
    CommissionGroupDetailView,
    CommissionGroupByCompanyListCreateView,
    CommissionGroupByCompanyManageView,
    CommissionGroupByUserManageView,
    CommissionGroupMaxRatesView,
    CommissionGroupByCompanyMaxRatesView,
)

from .comission import (
    CommissionListCreateView,
    CommissionDetailView,
    GenerateComissionsView,
    CommissionMirrorView,
    CommissionBalanceView,
)

from .payment import PaymentView, WithdrawView
from .corbanpay_withdraw import CorbanPayWithdrawView

from .form_fields import (
    CommissionGroupFormFieldsView,
    CommissionGroupByCompanyFormFieldsView,
    PaymentFormFieldsView,
)

__all__ = [
    'CommissionGroupListCreateView', 'CommissionGroupDetailView',
    'CommissionGroupByCompanyListCreateView', 'CommissionGroupByCompanyManageView',
    'CommissionGroupByUserManageView',
    'CommissionGroupMaxRatesView', 'CommissionGroupByCompanyMaxRatesView',
    'PaymentView', 'WithdrawView', 'CorbanPayWithdrawView',
    'CommissionListCreateView', 'CommissionDetailView', 'GenerateComissionsView',
    'CommissionMirrorView', 'CommissionBalanceView',
    'CommissionGroupFormFieldsView', 'CommissionGroupByCompanyFormFieldsView',
    'PaymentFormFieldsView',
]
