import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production')

# Keep DEBUG False for production security
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Permissive ALLOWED_HOSTS for Render
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'tenants',
    'accounts',
    'ingestion',
    'emissions',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOCAL_FRONTEND_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
PRODUCTION_FRONTEND_ORIGINS = [
    'https://breathe-esg-eosin.vercel.app',
]
VERCEL_FRONTEND_ORIGIN_REGEX = r'^https://[a-zA-Z0-9-]+\.vercel\.app$'


def csv_env(name, defaults=None):
    raw_value = os.environ.get(name)
    values = list(defaults or [])
    if raw_value:
        values.extend(item.strip() for item in raw_value.split(',') if item.strip())
    return list(dict.fromkeys(values))


# CORS - Specific origins are REQUIRED when CORS_ALLOW_CREDENTIALS is True.
# In local DEBUG mode include the Vite dev server origins automatically.
default_frontend_origins = (
    LOCAL_FRONTEND_ORIGINS + PRODUCTION_FRONTEND_ORIGINS
    if DEBUG
    else PRODUCTION_FRONTEND_ORIGINS
)
CORS_ALLOWED_ORIGINS = csv_env('CORS_ALLOWED_ORIGINS', default_frontend_origins)
CORS_ALLOWED_ORIGIN_REGEXES = csv_env(
    'CORS_ALLOWED_ORIGIN_REGEXES',
    [VERCEL_FRONTEND_ORIGIN_REGEX],
)
CORS_ALLOW_CREDENTIALS = True

# CSRF
CSRF_TRUSTED_ORIGINS = csv_env(
    'CSRF_TRUSTED_ORIGINS',
    default_frontend_origins + ['https://*.vercel.app'],
)

# Cookies for authentication.
# Production needs cross-site secure cookies for Vercel -> Render.
# Local development usually runs over plain HTTP, so secure cookies would be dropped.
SESSION_COOKIE_SAMESITE = 'Lax' if DEBUG else 'None'
CSRF_COOKIE_SAMESITE = 'Lax' if DEBUG else 'None'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Render Proxy SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
