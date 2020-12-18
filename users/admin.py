from django.contrib import admin
from django.contrib.auth import get_user_model, admin as auth_admin


@admin.register(get_user_model())
class UserAdmin(auth_admin.UserAdmin):
    pass
