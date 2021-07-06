from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.flatpages import views
from django.urls import path, include, re_path
import blender_id_oauth_client.urls

import blog.urls
import comments.urls
import films.urls
import search.urls
import looper.urls
import subscriptions.urls
import training.urls
import static_assets.urls
import users.urls

from common.views.home import home as home_view, welcome as welcome_view
import common.views.errors as error_views
from django.views.generic import TemplateView

admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE


urlpatterns = [
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
    path('oauth/', include(blender_id_oauth_client.urls)),
    path('', home_view, name='home'),
    path('welcome/', welcome_view, name='welcome'),
    path('comments/', include(comments.urls)),
    path('films/', include(films.urls)),
    path('training/', include(training.urls)),
    path('blog/', include(blog.urls)),
    path('search/', include(search.urls)),
    path('looper/', include((looper.urls), namespace='looper')),
    path('', include((subscriptions.urls), namespace='subscriptions')),
    path('', include(users.urls)),
    path('', include(static_assets.urls)),
    path('stats/', include('stats.urls')),
    path('activity/', include('actstream.urls')),
    re_path(r'^webhooks/', include('anymail.urls')),
    path('_nested_admin/', include('nested_admin.urls')),
    path('admin/', include('loginas.urls')),
]

handler400 = error_views.ErrorView.as_view(template_name='common/errors/400.html', status=400)
handler403 = error_views.ErrorView.as_view(template_name='common/errors/403.html', status=403)
handler404 = error_views.ErrorView.as_view(template_name='common/errors/404.html', status=404)
handler500 = error_views.ErrorView.as_view(template_name='common/errors/500.html', status=500)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Test different error pages by changing the template (400.html, 403.html, etc.)
    urlpatterns += [path('error', TemplateView.as_view(template_name='common/errors/404.html'))]

    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

# Flatpages catch-all
urlpatterns += [
    re_path(r'^(?P<url>.*/)$', views.flatpage),
]
