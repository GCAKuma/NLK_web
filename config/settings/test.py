from .base import *
# Deliberately ignore DATABASE_URL: tests must never connect to Supabase.
import os
DEBUG = True
SECRET_KEY = 'isolated-tests-only-' + 'x' * 60
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'HOST': 'test-db', 'PORT': '5432', 'NAME': 'nlk_test',
    'USER': 'nlk_test', 'PASSWORD': 'isolated-test-only',
}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
WHATSAPP_PROVIDER = 'console'
MEDIA_ROOT = '/tmp/nlk-test-media'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
