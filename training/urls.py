from django.urls import include, path

from training.views.api.comment import comment
from training.views.api.favorite import favorite
from training.views.api.progress import section_progress, video_progress
from training.views.home import home
from training.views.training.section import section
from training.views.training.training import training

urlpatterns = [
    path('', home, name='training-home'),
    path(
        'api/',
        include(
            [
                path('trainings/<int:training_pk>/favorite/', favorite, name='training-favorite'),
                path(
                    'sections/<int:section_pk>/',
                    include(
                        [
                            path('comment/', comment, name='section-comment'),
                            path('progress/', section_progress, name='section-progress'),
                        ]
                    ),
                ),
                path('videos/<int:video_pk>/progress/', video_progress, name='video-progress'),
            ]
        ),
    ),
    path(
        '<slug:training_slug>/',
        include(
            [
                path('', training, name='training'),
                path('<slug:section_slug>', section, name='section',),
            ]
        ),
    ),
]
