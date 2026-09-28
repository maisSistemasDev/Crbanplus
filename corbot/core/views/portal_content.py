from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from core.base_views import BaseApiView
from core.models import PortalUsefulLink, PortalWallMessage
from core.permissions import IsPromotoraUser
from core.serializers import PortalUsefulLinkSerializer, PortalWallMessageSerializer


class PortalUsefulLinkListCreateView(BaseApiView):
    """CRUD de links úteis para publicação no portal dos corbans."""

    permission_classes = [permissions.IsAuthenticated, IsPromotoraUser]

    def get(self, request):
        search = (request.GET.get('search') or '').strip()
        queryset = PortalUsefulLink.objects.all().order_by('display_order', '-created_at')
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(url__icontains=search))
        return Response(PortalUsefulLinkSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = PortalUsefulLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)

        self.log_info(
            request=request,
            action='create_portal_useful_link',
            message=f'Link útil criado para o portal: {serializer.validated_data.get("title", "")}',
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PortalUsefulLinkDetailView(BaseApiView):
    """Atualização e remoção de links úteis do portal."""

    permission_classes = [permissions.IsAuthenticated, IsPromotoraUser]

    def get_object(self, pk):
        return get_object_or_404(PortalUsefulLink, pk=pk)

    def patch(self, request, pk):
        instance = self.get_object(pk)
        serializer = PortalUsefulLinkSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.log_info(
            request=request,
            action='update_portal_useful_link',
            message=f'Link útil atualizado no portal: {instance.title}',
        )
        return Response(serializer.data)

    def delete(self, request, pk):
        instance = self.get_object(pk)
        title = instance.title
        instance.delete()

        self.log_info(
            request=request,
            action='delete_portal_useful_link',
            message=f'Link útil removido do portal: {title}',
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortalWallMessageListCreateView(BaseApiView):
    """CRUD de mensagens do mural para o portal dos corbans."""

    permission_classes = [permissions.IsAuthenticated, IsPromotoraUser]

    def get(self, request):
        search = (request.GET.get('search') or '').strip()
        queryset = PortalWallMessage.objects.select_related('company').all().order_by('display_order', '-created_at')
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(message__icontains=search))
        return Response(PortalWallMessageSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = PortalWallMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)

        self.log_info(
            request=request,
            action='create_portal_wall_message',
            message=f'Mensagem de mural criada para o portal: {serializer.validated_data.get("title", "")}',
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PortalWallMessageDetailView(BaseApiView):
    """Atualização e remoção de mensagens do mural do portal."""

    permission_classes = [permissions.IsAuthenticated, IsPromotoraUser]

    def get_object(self, pk):
        return get_object_or_404(PortalWallMessage, pk=pk)

    def patch(self, request, pk):
        instance = self.get_object(pk)
        serializer = PortalWallMessageSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.log_info(
            request=request,
            action='update_portal_wall_message',
            message=f'Mensagem de mural atualizada no portal: {instance.title}',
        )
        return Response(serializer.data)

    def delete(self, request, pk):
        instance = self.get_object(pk)
        title = instance.title
        instance.delete()

        self.log_info(
            request=request,
            action='delete_portal_wall_message',
            message=f'Mensagem de mural removida do portal: {title}',
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortalContentFeedView(BaseApiView):
    """Feed consumido pelo portal dos corbans (links úteis e mural ativos)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        links = PortalUsefulLink.objects.filter(is_active=True).order_by('display_order', '-created_at')

        messages = PortalWallMessage.objects.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        )

        if request.user.company_id:
            messages = messages.filter(Q(company__isnull=True) | Q(company_id=request.user.company_id))

        messages = messages.select_related('company').order_by('display_order', '-created_at')

        return Response(
            {
                'links': PortalUsefulLinkSerializer(links, many=True).data,
                'wall_messages': PortalWallMessageSerializer(messages, many=True).data,
            }
        )
