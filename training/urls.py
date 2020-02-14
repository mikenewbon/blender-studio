"""training URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from training_main.views.home import home
from training_main.views.trainings.chapters.chapter import chapter
from training_main.views.trainings.chapters.sections.section import section
from training_main.views.trainings.training import training

urlpatterns = [
    path('admin/', admin.site.urls),
    path('oauth/', include('blender_id_oauth_client.urls')),
]

urlpatterns += [
    path('', home, name='home'),
    path(
        'trainings/<slug:training_slug>/',
        include(
            [
                path('', training, name='training'),
                path(
                    'chapters/<int:chapter_index>-<slug:chapter_slug>/',
                    include(
                        [
                            path('', chapter, name='chapter'),
                            path(
                                'sections/<int:section_index>-<slug:section_slug>/',
                                include([path('', section, name='section')]),
                            ),
                        ]
                    ),
                ),
            ]
        ),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
