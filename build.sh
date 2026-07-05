#!/usr/bin/env bash
pip install -r requirements.txt
cd waiter_app
python manage.py collectstatic --no-input
python manage.py migrate