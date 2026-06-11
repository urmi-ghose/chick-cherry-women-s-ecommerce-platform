@echo off
start "Email Service" cmd /k "cd /d %~dp0 && npm run dev"
start "Store Server" cmd /k "cd /d %~dp0 && env\Scripts\activate && python manage.py runserver 8000 --settings=ecommerce.settings_store"
start "Admin Server" cmd /k "cd /d %~dp0 && env\Scripts\activate && python manage.py runserver 8001 --settings=ecommerce.settings_admin"
