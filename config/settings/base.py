"""
Configuration Django de base â€” commune Ã  tous les environnements.
Tous les secrets sont lus depuis .env via python-decouple.
"""
from decimal import Decimal
from pathlib import Path

from decouple import Csv, config

# ============================================================
# CHEMINS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================
# SÃ‰CURITÃ‰
# ============================================================
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# ============================================================
# APPLICATIONS
# ============================================================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'modeltranslation',   # i18n FR/EN sur champs de modÃ¨les
]

LOCAL_APPS = [
    'accounts.apps.AccountsConfig',   # config explicite pour ready() â†’ signaux
    'conference.apps.ConferenceConfig',
    'reservations.apps.ReservationsConfig',
    'payments.apps.PaymentsConfig',
    'tickets.apps.TicketsConfig',
    'dashboard.apps.DashboardConfig',
    'notifications',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ============================================================
# MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',      # i18n FR/EN
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ============================================================
# TEMPLATES
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.static',
                'config.context_processors.whatsapp_contact',
              ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ============================================================
# BASE DE DONNÃ‰ES (SQLite en dev, PostgreSQL en prod via DATABASE_URL)
# ============================================================
import dj_database_url  # noqa: E402

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# ============================================================
# AUTHENTIFICATION
# ============================================================
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard'
LOGOUT_REDIRECT_URL = 'conference:home'

# ============================================================
# INTERNATIONALISATION (FR / EN)
# ============================================================
LANGUAGE_CODE = 'fr'
LANGUAGES = [
    ('fr', 'FranÃ§ais'),
    ('en', 'English'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Africa/Kinshasa'
USE_I18N = True
USE_TZ = True

# ============================================================
# FICHIERS STATIQUES & MÃ‰DIAS
# ============================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# EMAIL (Gmail SMTP en prod, console en dev)
# ============================================================
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='kalumemmanueljohn@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='clrc rlyq gnkh dnjz')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

# ============================================================
# VARIABLES MÃ‰TIER (Bantondo's GÃ©nÃ©ration ASBL)
# ============================================================
# ConfÃ©rence payante en USD
DEFAULT_CURRENCY = 'USD'
CONFERENCE_PRICE_PER_SEAT = Decimal('5.70')   # valeur par dÃ©faut, surchargeable en DB
MAX_SEATS_PER_RESERVATION = 5

# SASPAY
# SASPAY
SASPAY_API_KEY = config('SASPAY_API_KEY', default='')
SASPAY_SECRET_KEY = config('SASPAY_SECRET_KEY', default='')
SASPAY_BASE_URL = config('SASPAY_BASE_URL', default='')
SASPAY_WEBHOOK_SECRET = config('SASPAY_WEBHOOK_SECRET', default='')

# SASPAY — Configuration par défaut
SASPAY_DEFAULT_NETWORK = config('SASPAY_DEFAULT_NETWORK', default='vodacom_cd_usd')
SASPAY_DEFAULT_COUNTRY = config('SASPAY_DEFAULT_COUNTRY', default='XC')
SASPAY_DEFAULT_CURRENCY = config('SASPAY_DEFAULT_CURRENCY', default='USD')

# WhatsApp
WHATSAPP_PAYMENT_NUMBER = config('WHATSAPP_PAYMENT_NUMBER', default='+243830360200')

WHATSAPP_PAYMENT_NUMBER = config('WHATSAPP_PAYMENT_NUMBER', default='')
WHATSAPP_ADMIN_NUMBER = config('WHATSAPP_ADMIN_NUMBER', default='')

# ============================================================
# LOGGING (sÃ©parÃ© par domaine)
# ============================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'reservations': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
        'payments':     {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
        'tickets':      {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
        'security':     {'handlers': ['console', 'file'], 'level': 'WARNING', 'propagate': False},
    },
}
