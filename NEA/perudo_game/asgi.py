"""
ASGI config for perudo_game project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

#Sets the default django settings to the settings.py file
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perudo_game.settings')

application = get_asgi_application()
