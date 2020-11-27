from django.urls.conf import path

from static_assets.views import video_progress, coconut_webhook

urlpatterns = [
    path('api/videos/<int:video_pk>/progress/', video_progress, name='video-progress'),
    # Video Processing webhook
    path('api/videos/<int:video_id>/processing/', coconut_webhook, name='coconut-webhook',),
]
