from django.urls import path
from .views import api_docs

urlpatterns = [
    path('', api_docs, name='api_docs'),
] 