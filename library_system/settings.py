import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-+u-h%_48mb5+quh+b#3crq^klglzmu77b!aqo&mflgd(wm(&bw')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,vitaltyrsu.pythonanywhere.com').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'import_export',
    'library.apps.LibraryConfig',
    # django-allauth apps for Google Sign-In
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Required for django-allauth
]

ROOT_URLCONF = 'library_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'library' / 'templates'],
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

WSGI_APPLICATION = 'library_system.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (uploaded images)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'library.User'

# Redirect to login page if not authenticated
LOGIN_URL = 'student_login'

# django-allauth configuration
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

SITE_ID = 1

# allauth settings - simplified for Google-only sign in
ACCOUNT_EMAIL_VERIFICATION = 'none'  # rely on Google verification for beta
ACCOUNT_LOGIN_METHODS = {'email'}  # Updated setting (replaces ACCOUNT_AUTHENTICATION_METHOD)
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*']  # Updated setting (replaces ACCOUNT_EMAIL_REQUIRED)
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True  # Automatically create accounts on first Google sign-in

# Use environment variables for client credentials in production
SOCIAL_AUTH_GOOGLE_CLIENT_ID = os.environ.get('SOCIAL_AUTH_GOOGLE_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_CLIENT_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_CLIENT_SECRET', '')

# Optional: restrict signups to a specific domain (set in environment or later)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# Skip the intermediate "Sign in with Google" confirmation page
# Set to False if you want users to see a confirmation page before redirecting to Google
SOCIALACCOUNT_LOGIN_ON_GET = False  # Redirect directly to Google without confirmation

# Redirect URLs after login/logout
LOGIN_REDIRECT_URL = '/catalog/'  # Redirect to book catalog after successful login
ACCOUNT_LOGOUT_REDIRECT_URL = '/login/'  # Redirect to login page after logout
LOGIN_URL = '/login/'  # Where to redirect if login is required

# ===================================
# EMAIL CONFIGURATION
# ===================================
# For development: Console backend (prints emails to console)
# For production: Configure SMTP settings

# Production: Use SMTP with Gmail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'vital.tyrsu@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')  # Loaded from .env file

# Default from email address
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'vital.tyrsu@gmail.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Email notification settings
SEND_RESERVATION_EMAILS = True
SEND_DUE_DATE_REMINDERS = True
SEND_OVERDUE_NOTIFICATIONS = True

# Note: For Gmail in production, you'll need to:
# 1. Enable 2-factor authentication on your Gmail account
# 2. Generate an "App Password" at https://myaccount.google.com/apppasswords
# 3. Set environment variables:
#    - EMAIL_HOST_USER=vital.tyrsu@gmail.com
#    - EMAIL_HOST_PASSWORD=your_app_password (16-character code from Google)