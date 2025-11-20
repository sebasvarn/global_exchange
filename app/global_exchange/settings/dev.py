from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
SITE_URL = "http://localhost:8000"

# Allow overriding email backend from environment (so .env.dev can enable SMTP)
import os
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")

CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]
