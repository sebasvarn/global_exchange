from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env.dev')

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-not-secure")
DEBUG = False

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if os.getenv("DJANGO_ALLOWED_HOSTS") else []

INSTALLED_APPS = [
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "widget_tweaks",
    "usuarios","clientes","commons","payments","monedas","medios_acreditacion", "transaccion",
    # MFA app
    "mfa",
    "tauser",  # Added tauser app
]

AUTH_USER_MODEL = "usuarios.User"

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@tu-dominio.com")
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

# === Stripe (modo test) ===
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")  # sk_test_...
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")  # whsec_...

# Usamos SITE_URL para formar las URLs de retorno
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", f"{SITE_URL}/pagos/success/")
STRIPE_CANCEL_URL  = os.getenv("STRIPE_CANCEL_URL",  f"{SITE_URL}/pagos/cancel/")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    'usuarios.middleware.MfaRequiredMiddleware',
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "global_exchange.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "global_exchange.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Asuncion"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
from glob import glob
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
# Agregar automáticamente todas las carpetas static de apps dentro de /app
for static_dir in glob(str(BASE_DIR / "app" / "*" / "static")):
    STATICFILES_DIRS.append(static_dir)
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# MFA defaults
MFA_DEFAULT_TTL_SECONDS = int(os.getenv('MFA_DEFAULT_TTL_SECONDS', '300'))
MFA_CODE_LENGTH = int(os.getenv('MFA_CODE_LENGTH', '6'))
MFA_MAX_ATTEMPTS = int(os.getenv('MFA_MAX_ATTEMPTS', '5'))
MFA_RESEND_LIMIT = int(os.getenv('MFA_RESEND_LIMIT', '3'))
MFA_RESEND_BLOCK_TTL = int(os.getenv('MFA_RESEND_BLOCK_TTL', '900'))


_csrf = os.getenv("CSRF_TRUSTED_ORIGINS")
CSRF_TRUSTED_ORIGINS = _csrf.split(",") if _csrf else []
