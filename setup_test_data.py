"""
Run this once to create tenant, user, and load sample data.
python setup_test_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tenants.models import Tenant
from accounts.models import User

# Create tenant
tenant, _ = Tenant.objects.get_or_create(
    slug='demo-client',
    defaults={'name': 'Demo Client Ltd'}
)

# Create analyst user
if not User.objects.filter(username='analyst').exists():
    user = User.objects.create_user(
        username='analyst',
        password='breathe2024',
        tenant=tenant,
        role='analyst',
        email='analyst@democlient.com'
    )
    print(f'Created user: analyst / breathe2024')

print(f'Tenant: {tenant.name}')
print('Setup complete.')