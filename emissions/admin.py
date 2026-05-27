from django.contrib import admin
from .models import NormalizedEmission, EmissionAuditLog

admin.site.register(NormalizedEmission)
admin.site.register(EmissionAuditLog)