"""
Views relacionadas a operações com líderes.
Incluindo listagem de líderes e alteração de líderes para vendedores.
"""
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from core.base_views import BaseApiView
from core.models import User, Company
from core.serializers import UserSerializer, UserListSerializer
from core.permissions import IsAdminOrGerente
from payments.models import CommissionGroup

class LideresCreateListView(BaseApiView):
    """
    API endpoint para listar líderes.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk):
        user = get_object_or_404(User, pk=pk)
        self.check_object_permissions(self.request, user)
        return user
    
    def get(self, request, format=None):
        """
        Lista todos os líderes.
        """
        company = request.GET.get('company')
        if request.user.role == User.ADMIN:
            lideres = User.objects.filter(role=User.LIDER)
        elif request.user.role == User.EMPRESA_ADMIN:
            lideres = User.objects.filter(role=User.LIDER, company=request.user.company)
        elif company:
            lideres = User.objects.filter(role=User.LIDER, company=company)
        else:
            company = request.user.company
            lideres = User.objects.filter(role=User.LIDER, company=company)
        serializer = UserListSerializer(lideres, many=True)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='list_lideres',
            message=f'Usuário listou {lideres.count()} líderes'
        )
        
        return Response(serializer.data)
    def post(self, request, format=None):
        company = request.data.get('company')
        if(request.user.role == User.ADMIN and not company):
            return Response(
                {"detail": "A empresa é obrigatória para criar um líder."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if(request.user.role != User.ADMIN):
            company = request.user.company
        else:
            company = Company.objects.get(id=company)
        user = User.objects.create(
            company=company,
            role=User.LIDER,
            cpf=request.data.get('cpf'),
            first_name=request.data.get('first_name'),
            last_name=request.data.get('last_name'),
            email=request.data.get('email'),
        )
        user.set_password(request.data.get('password'))
        user.save()
        return Response(
            {"detail": "Líder criado com sucesso."},
            status=status.HTTP_201_CREATED
        )
            

class ChangeLeaderView(BaseApiView):
    """
    API endpoint para alterar o líder de um vendedor.
    """
    permission_classes = [IsAdminOrGerente]
    
    def post(self, request, pk, format=None):
        """
        Altera o líder de um vendedor.
        """
        user = get_object_or_404(User, pk=pk)
        
        if user.role != User.VENDEDOR:
            return Response(
                {"detail": "Apenas vendedores podem ter líderes alterados."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Captura os dados antes da atualização
        old_data = UserSerializer(user).data
        
        leader_id = request.data.get('leader_id')
        
        if leader_id:
            try:
                leader = User.objects.get(id=leader_id, role=User.LIDER)
                user.leader = leader
                user.save()
                
                # Captura os dados após a atualização
                new_data = UserSerializer(user).data
                
                # Registra a auditoria usando o método da classe base
                self.audit_update(
                    request=request,
                    instance=user,
                    data_before=old_data,
                    data_after=new_data
                )
                
                # Registra a ação usando o método da classe base
                self.log_info(
                    request=request,
                    action='change_leader',
                    message=f'Usuário alterou o líder do vendedor {user.cpf} para {leader.cpf}',
                    data={'user_id': user.id, 'leader_id': leader.id}
                )
                
                return Response({"detail": "Líder alterado com sucesso."})
            except User.DoesNotExist:
                return Response(
                    {"detail": "Líder não encontrado."},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            old_leader = user.leader
            user.leader = None
            user.save()
            
            # Captura os dados após a atualização
            new_data = UserSerializer(user).data
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=user,
                data_before=old_data,
                data_after=new_data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='remove_leader',
                message=f'Usuário removeu o líder do vendedor {user.cpf}',
                data={'user_id': user.id, 'old_leader_id': old_leader.id if old_leader else None}
            )
            
            return Response({"detail": "Líder removido com sucesso."})


class BatchChangeLeaderView(BaseApiView):
    """
    API endpoint para alterar o líder de vários vendedores de uma vez.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, format=None):
        """
        Altera o líder de vários vendedores de uma vez.
        """
        leader_id = request.data.get('leader_id')
        seller_ids = request.data.get('sellers_ids', [])

        if not leader_id:
            return Response(
                {"detail": "ID do líder é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(seller_ids):
            leader = User.objects.get(id=leader_id, role=User.LIDER)
            User.objects.filter(leader=leader).update(leader=None)
            return Response(
                {"detail": "Equipe removida com sucesso."},
                status=status.HTTP_200_OK
            )
            
        if not seller_ids or not isinstance(seller_ids, list):
            return Response(
                {"detail": "Lista de IDs de vendedores é obrigatória."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            leader = User.objects.get(id=leader_id, role=User.LIDER)
            
            # Verificar se o líder pertence à mesma empresa do usuário logado
            if leader.company != request.user.company:
                return Response(
                    {"detail": "O líder deve pertencer à mesma empresa do usuário logado."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            company = request.user.company
            result = {
                "success": [],
                "errors": []
            }
            #Não remove os vendedores que já estão no grupo de comissionamento
            sellers_in_group = User.objects.filter(leader=leader, role=User.VENDEDOR, company=company).exclude(id__in=seller_ids)
            
            excluded_sellers = User.objects.filter(id__in=[seller.id for seller in sellers_in_group if seller.id not in seller_ids], role=User.VENDEDOR, company=company)
            excluded_sellers.update(leader=None)
            for seller in excluded_sellers:
                #Verifica se o vendedor está em um grupo de comissionamento
                commission_group = CommissionGroup.objects.filter(sellers=seller, by_leader=True).first()
                if commission_group:
                    #Se estiver, remove o vendedor do grupo de comissionamento
                    commission_group.sellers.remove(seller)
                    commission_group.save()
                    #Adiciona o vendedor ao grupo de comissionamento padrão
                    default_group = CommissionGroup.objects.filter(company=company, by_leader=False, leader=leader).first()
                    if default_group:
                        default_group.sellers.add(seller)
                        default_group.save()
                        
            for seller_id in seller_ids:
                try:
                    commission_group_leader = CommissionGroup.objects.filter(leaders=leader).first()
                    if(seller_id not in [seller.id for seller in sellers_in_group]):
                        
                        seller = User.objects.get(id=seller_id, role=User.VENDEDOR, company=company)
                        old_commission_group = CommissionGroup.objects.filter(sellers=seller).first()
                        if old_commission_group:
                            old_commission_group.sellers.remove(seller)
                            old_commission_group.save()
                        # Captura os dados antes da atualização
                        old_data = UserSerializer(seller).data
                        
                        seller.leader = leader
                        seller.save()
                        
                        if commission_group_leader:
                            commission_group_leader.sellers.add(seller)
                            commission_group_leader.save()
                        
                        # Captura os dados após a atualização
                        new_data = UserSerializer(seller).data
                        
                        # Registra a auditoria
                        self.audit_update(
                            request=request,
                            instance=seller,
                            data_before=old_data,
                            data_after=new_data
                        )
                        
                        # Adiciona à lista de sucesso
                        result["success"].append({
                            "id": seller_id,
                            "name": f"{seller.first_name} {seller.last_name}".strip() or seller.cpf
                        })
                    
                except User.DoesNotExist:
                    # Adiciona à lista de erros
                    result["errors"].append({
                        "id": seller_id,
                        "error": "Vendedor não encontrado ou não pertence à sua empresa."
                    })
            
            # Registra a ação completa
            self.log_info(
                request=request,
                action='batch_change_leader',
                message=f'Usuário alterou o líder de {len(result["success"])} vendedores para {leader.cpf}',
                data={
                    'leader_id': leader.id,
                    'success_count': len(result["success"]),
                    'error_count': len(result["errors"])
                }
            )
            
            return Response(result)
            
        except User.DoesNotExist:
            return Response(
                {"detail": "Líder não encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, format=None):
        """
        Lista todos os vendedores.
        """
        leader_id = request.GET.get('leader_id')
        if leader_id:
            leader = User.objects.filter(id=leader_id, role=User.LIDER).first()
            if not leader:
                return Response(
                    {"detail": "Líder não encontrado."},
                    status=status.HTTP_404_NOT_FOUND
                )
            company = leader.company
            sellers = User.objects.filter(role=User.VENDEDOR, company=company).exclude(leader=leader)
            my_sellers = User.objects.filter(role=User.VENDEDOR, leader=leader)
        serializer = UserListSerializer(sellers, many=True)
        return Response({
            'sellers': serializer.data,
            'my_sellers': UserListSerializer(my_sellers, many=True).data
        }) 