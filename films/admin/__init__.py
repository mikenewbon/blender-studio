from django.contrib import admin

from films.admin.films import *
from films.admin.mixins import *
from films.admin.production_logs import *
from films.models import assets

admin.site.register(assets.Asset)
