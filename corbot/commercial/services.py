from core.models import User
from .models import CommercialTeamMember


def team_company_ids_for(user) -> list:
    """UUIDs dos corbans na carteira do gerente comercial."""
    if not user or getattr(user, 'role', None) != User.GERENTE_COMERCIAL:
        return []
    return list(
        CommercialTeamMember.objects.filter(manager=user).values_list('company_id', flat=True)
    )


def clear_manager_team(manager: User) -> int:
    """Remove todos os vínculos da equipe. Corbans ficam sem gerente."""
    deleted, _ = CommercialTeamMember.objects.filter(manager=manager).delete()
    return deleted
