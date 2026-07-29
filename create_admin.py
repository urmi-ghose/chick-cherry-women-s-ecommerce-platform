import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from accounts.models import Account

# Use a new email and password
first_name = 'Admin'
last_name = 'User'
username = 'adminuser'
email = 'newadmin@example.com'
password = 'password123'

if not Account.objects.filter(email=email).exists():
    Account.objects.create_superuser(
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=username,
        password=password
    )
    print("Superuser created successfully with email:", email)
else:
    print("Email already exists")
