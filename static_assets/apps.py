from django.apps import AppConfig

import mimetypes

# Overwrite some possibly missing mimetypes
mimetypes.add_type('application/x-blender', '.blend')
mimetypes.add_type('application/x-radiance-hdr', '.hdr')
mimetypes.add_type('application/x-exr', '.exr')


class AssetsConfig(AppConfig):
    name = 'static_assets'
    verbose_name = 'Static Assets'
