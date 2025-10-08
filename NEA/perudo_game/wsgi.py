"""
WSGI config for perudo_game project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

#Sets the default django settings to the settings.py file
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perudo_game.settings')

application = get_wsgi_application()
