from django.contrib import admin
from .models import User, Nominee, Credentials



# Register your models here.
admin.site.register(User)
admin.site.register(Nominee)
admin.site.register(Credentials)


