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

from training_main.views.api.comments.delete import comment_delete
from training_main.views.api.comments.edit import comment_edit
from training_main.views.api.comments.like import comment_like
from training_main.views.api.sections.comment import comment
from training_main.views.api.trainings.favorite import favorite
from training_main.views.api.videos.progress import video_progress, section_progress
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
        'api/',
        include(
            [
                path('trainings/<int:training_pk>/favorite/', favorite, name='training_favorite'),
                path(
                    'sections/<int:section_pk>/',
                    include(
                        [
                            path('comment/', comment, name='section_comment'),
                            path('progress/', section_progress, name='section_progress'),
                        ]
                    ),
                ),
                path(
                    'comments/<int:comment_pk>/',
                    include(
                        [
                            path('like/', comment_like, name='comment_like'),
                            path('edit/', comment_edit, name='comment_edit'),
                            path('delete/', comment_delete, name='comment_delete'),
                        ]
                    ),
                ),
                path('videos/<int:video_pk>/progress/', video_progress, name='video_progress'),
            ]
        ),
    ),
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
