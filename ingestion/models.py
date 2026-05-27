import uuid
from django.db import models
from django.conf import settings


class RawIngestion(models.Model):

    SOURCE_TYPES = [
        ('SAP', 'SAP Fuel and Procurement'),
        ('UTILITY', 'Utility Electricity'),
        ('TRAVEL', 'Corporate Travel'),
    ]

    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    raw_content = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    row_count_total = models.IntegerField(default=0)
    row_count_success = models.IntegerField(default=0)
    row_count_failed = models.IntegerField(default=0)
    error_log = models.JSONField(default=list)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.source_type} | {self.original_filename} | {self.uploaded_at:%Y-%m-%d}"