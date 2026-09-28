"""
Views de sinistro (claim) em propostas.
"""
from rest_framework import permissions, status
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.permissions import IsAdmin
from core.search_utils import paginate_queryset
from payments.models import ProposalClaim
from payments.serializers import ProposalClaimSerializer
from payments.services.claims import ClaimError, register_claim
from proposals.models import Proposal


class ProposalClaimListCreateView(BaseApiView):
    """Lista sinistros e registra novos (fraude ou pago ao corban errado)."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request):
        claims = ProposalClaim.objects.select_related(
            'proposal', 'charged_company', 'correct_company', 'created_by', 'debit'
        ).all()

        proposal_id = request.query_params.get('proposal')
        if proposal_id:
            claims = claims.filter(proposal_id=proposal_id)

        claim_type = request.query_params.get('claim_type')
        if claim_type:
            claims = claims.filter(claim_type=claim_type)

        return paginate_queryset(request, claims, ProposalClaimSerializer)

    def post(self, request):
        proposal_id = request.data.get('proposal')
        claim_type = request.data.get('claim_type')

        if not proposal_id:
            return Response({'detail': 'Proposta é obrigatória.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            proposal = Proposal.objects.select_related('company').get(id=proposal_id)
        except Proposal.DoesNotExist:
            return Response({'detail': 'Proposta não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            claim = register_claim(
                proposal=proposal,
                claim_type=claim_type,
                actor=request.user,
                description=(request.data.get('description') or '').strip(),
                correct_company_id=request.data.get('correct_company'),
            )
        except ClaimError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        data = ProposalClaimSerializer(claim).data
        self.audit_create(request=request, instance=claim, data_after=data)
        self.log_info(
            request=request,
            action='create_proposal_claim',
            message=f'Sinistro {claim.get_claim_type_display()} registrado na proposta {proposal.id}',
            data={
                'claim_id': claim.id,
                'proposal_id': str(proposal.id),
                'claim_type': claim.claim_type,
                'amount': str(claim.amount),
                'debit_id': claim.debit_id,
            },
        )
        return Response(data, status=status.HTTP_201_CREATED)
