from django.urls import path

from .views import (
    TableSuggestionListView,
    TableSuggestionAcceptView,
    TableSuggestionRejectView,
    ConversationListCreateView,
    ConversationDetailView,
)

urlpatterns = [
    # Sugestões de atualização de tabela
    path('ai/suggestions/', TableSuggestionListView.as_view(), name='ai-suggestion-list'),
    path('ai/suggestions/<int:pk>/accept/', TableSuggestionAcceptView.as_view(), name='ai-suggestion-accept'),
    path('ai/suggestions/<int:pk>/reject/', TableSuggestionRejectView.as_view(), name='ai-suggestion-reject'),

    # Conversas com o agente
    path('ai/conversations/', ConversationListCreateView.as_view(), name='ai-conversation-list'),
    path('ai/conversations/<int:pk>/', ConversationDetailView.as_view(), name='ai-conversation-detail'),
]
