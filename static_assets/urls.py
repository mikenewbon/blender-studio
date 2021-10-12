from django.urls.conf import path

from static_assets.views import video_progress, coconut_webhook, video_track_view

urlpatterns = [
    path('api/videos/<int:video_pk>/progress/', video_progress, name='video-progress'),
    # Video Processing webhook
    path('api/videos/<int:video_id>/processing/', coconut_webhook, name='coconut-webhook'),
    # Video tracks served from a different domain require "crossorigin" attribute set on <video>,
    # so tracks are served from the same domain to avoid having CORS set up at the CDN for
    # all the videos as well as tracks.
    # See https://developer.mozilla.org/en-US/docs/Web/HTML/Element/track#attr-src
    path('media/videos/track/<int:pk>/', video_track_view, name='video-track'),
]
