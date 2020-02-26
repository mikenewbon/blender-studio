from django.urls import path, include

from training.views.api.comment import comment
from training.views.api.favorite import favorite
from training.views.api.progress import section_progress, video_progress
from training.views.home import home
from training.views.training.chapter import chapter
from training.views.training.section import section
from training.views.training.training import training

urlpatterns = [
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
