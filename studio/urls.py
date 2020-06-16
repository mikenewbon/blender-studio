import blender_id_oauth_client.urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

import comments.urls
import films.urls
import subscriptions.urls
import training.urls
import films.urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('oauth/', include(blender_id_oauth_client.urls)),
    path('', TemplateView.as_view(template_name="common/home.html")),
    path('welcome/', TemplateView.as_view(template_name="common/welcome.html")),
    path('comments/', include(comments.urls)),
    path('films/', include(films.urls)),
    path('training/', include(training.urls)),
    path('films/', include(films.urls)),
    path('subscriptions/', include(subscriptions.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
