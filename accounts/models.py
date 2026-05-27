from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    role = models.CharField(
        max_length=20,
        choices=[('analyst', 'Analyst'), ('admin', 'Admin')],
        default='analyst'
    )

    def __str__(self):
        return f"{self.username} ({self.tenant})"