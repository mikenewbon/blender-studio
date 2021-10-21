from django.apps import AppConfig

import mimetypes

# Overwrite some possibly missing mimetypes
mimetypes.add_type('application/x-blender', '.blend')
mimetypes.add_type('application/x-radiance-hdr', '.hdr')
mimetypes.add_type('application/x-exr', '.exr')
mimetypes.add_type('application/x-krita', '.kra')
mimetypes.add_type('audio/wav', '.wav')
mimetypes.add_type('video/mp4', '.m4v')


class AssetsConfig(AppConfig):
    name = 'static_assets'
    verbose_name = 'Static Assets'
