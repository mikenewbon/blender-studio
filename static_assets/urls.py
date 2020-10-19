from django.urls.conf import path

from static_assets.views import video_progress

urlpatterns = [
    path('api/videos/<int:video_pk>/progress/', video_progress, name='video-progress'),
]
