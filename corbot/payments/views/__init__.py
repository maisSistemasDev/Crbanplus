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
    CommissionConsolidatedView,
    CommissionDebitDetailView,
    CommissionBalanceView,
)

from .payment import PaymentView, WithdrawView
from .debit import UserDebitListCreateView, UserDebitDetailView
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
    'UserDebitListCreateView', 'UserDebitDetailView',
    'CommissionListCreateView', 'CommissionDetailView', 'GenerateComissionsView',
    'CommissionMirrorView', 'CommissionConsolidatedView', 'CommissionDebitDetailView',
    'CommissionBalanceView',
    'CommissionGroupFormFieldsView', 'CommissionGroupByCompanyFormFieldsView',
    'PaymentFormFieldsView',
]
