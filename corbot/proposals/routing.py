from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/proposal_batch/(?P<batch_id>[^/]+)/$', consumers.BatchProcessingConsumer.as_asgi()),
    re_path(r'ws/proposals/batch/(?P<batch_id>[^/]+)/$', consumers.BatchProcessingConsumer.as_asgi()),
] 