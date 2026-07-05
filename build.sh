#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
cd waiter_app
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed
echo "
from django.contrib.auth.models import User
from core.models import UserProfile
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', '', 'Bishal@2030')
    p, _ = UserProfile.objects.get_or_create(user=u)
    p.role = 'admin'
    p.save()
    print('Admin created!')
else:
    u = User.objects.get(username='admin')
    p, _ = UserProfile.objects.get_or_create(user=u)
    p.role = 'admin'
    p.save()
    print('Admin role updated!')
" | python manage.py shell