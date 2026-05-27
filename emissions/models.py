import uuid
from django.db import models
from django.conf import settings


class NormalizedEmission(models.Model):

    SCOPE_CHOICES = [(1, 'Scope 1'), (2, 'Scope 2'), (3, 'Scope 3')]

    SOURCE_TYPES = [
        ('SAP', 'SAP Fuel and Procurement'),
        ('UTILITY', 'Utility Electricity'),
        ('TRAVEL', 'Corporate Travel'),
    ]

    REVIEW_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('locked', 'Locked for Audit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    # Where this row came from
    raw_ingestion = models.ForeignKey(
        'ingestion.RawIngestion',
        on_delete=models.CASCADE,
        related_name='normalized_emissions'
    )
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    source_row_reference = models.CharField(max_length=100, blank=True)

    # GHG classification
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=100)
    activity_description = models.TextField()

    # Time period
    period_start = models.DateField()
    period_end = models.DateField()

    # Original values as ingested
    quantity_original = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )
    unit_original = models.CharField(max_length=20, blank=True)

    # After unit normalization
    quantity_normalized = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )
    unit_normalized = models.CharField(max_length=20, blank=True)
    conversion_applied = models.TextField(blank=True)

    # Emission calculation
    emission_factor_used = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    emission_factor_unit = models.CharField(max_length=50, blank=True)
    emission_factor_source = models.CharField(max_length=100, blank=True)
    co2e_kg = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )

    # Quality
    confidence_score = models.FloatField(default=1.0)
    flags = models.JSONField(default=list)

    # Review workflow
    review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUS, default='pending'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_emissions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_emissions'
    )

    # Extra source-specific fields that dont fit the schema
    metadata = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_start', 'scope']

    def __str__(self):
        return f"Scope {self.scope} | {self.source_type} | {self.co2e_kg} kg CO2e"


class EmissionAuditLog(models.Model):

    ACTIONS = [
        ('created', 'Created'),
        ('edited', 'Edited'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('locked', 'Locked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emission = models.ForeignKey(
        NormalizedEmission,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTIONS)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['performed_at']