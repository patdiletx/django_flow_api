"""
Django settings for flow_project project.
"""
import os
from pathlib import Path
from urllib.parse import urlparse # Para procesar URLs para CORS/CSRF

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Clave Secreta de Django ---
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'una-clave-secreta-por-defecto-solo-para-desarrollo-local-cambiar')

# --- Modo Debug ---
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# --- Hosts Permitidos ---
ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]

# --- URLs Base Configurables desde el Entorno ---
PUBLIC_URL_BASE = os.getenv('PUBLIC_URL_BASE', 'http://localhost:8000')
FUNGIFRESH_STORE_URL = os.getenv('FUNGIFRESH_STORE_URL', 'http://localhost:3000')


# --- Application definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', 
    'django.contrib.staticfiles',
    
    # Apps de Terceros
    'rest_framework',
    'corsheaders',
    # 'storages', # Ya no es necesario si no subes archivos a S3 desde Django
    
    # Mis Apps
    'payments.apps.PaymentsConfig',
    'products.apps.ProductsConfig',
    'blog.apps.BlogConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'flow_project.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'flow_project.wsgi.application'


# --- Base de Datos ---
DB_MOUNT_DIR_STR = os.getenv('SQLITE_DB_MOUNT_PATH', str(BASE_DIR))
DB_MOUNT_DIR = Path(DB_MOUNT_DIR_STR)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_MOUNT_DIR / 'db.sqlite3',
    }
}

# --- Configuración de Email ---
EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT_STR = os.getenv('EMAIL_PORT', '587')
try:
    EMAIL_PORT = int(EMAIL_PORT_STR)
except ValueError:
    EMAIL_PORT = 587
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'webmaster@localhost')
STORE_OWNER_EMAIL = os.getenv('STORE_OWNER_EMAIL')

# --- Configuración de n8n ---
N8N_SALE_WEBHOOK_URL = os.getenv('N8N_SALE_WEBHOOK_URL')

# --- Configuración de Archivos Media (para subidas locales si alguna vez se usan) ---
# Como ahora usas URLField para la imagen principal del blog/producto,
# estas configuraciones son más para un posible uso futuro de FileField/ImageField
# o para desarrollo local de otras funcionalidades.
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage' # Volvemos al default de Django
MEDIA_URL = '/media/' # URL base para servir archivos media localmente
MEDIA_ROOT = BASE_DIR / 'mediafiles' # Carpeta donde se guardarían localmente
if DEBUG and not os.path.exists(MEDIA_ROOT): # Crear la carpeta en desarrollo si no existe
    os.makedirs(MEDIA_ROOT)


# --- Archivos Estáticos (CSS, JavaScript, Imágenes del admin y de tus apps) ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Configuración de CORS ---
CORS_ALLOWED_ORIGINS_STRING = os.getenv('DJANGO_CORS_ALLOWED_ORIGINS')
if CORS_ALLOWED_ORIGINS_STRING:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS_STRING.split(',') if origin.strip()]
else:
    CORS_ALLOWED_ORIGINS = []
    if DEBUG:
        CORS_ALLOWED_ORIGINS.extend([
            "http://localhost:3000", "http://127.0.0.1:3000",
            "http://localhost:8080", "http://127.0.0.1:8080",
        ])

if PUBLIC_URL_BASE and PUBLIC_URL_BASE not in CORS_ALLOWED_ORIGINS:
    parsed_public_url = urlparse(PUBLIC_URL_BASE)
    origin_from_public_url = f"{parsed_public_url.scheme}://{parsed_public_url.netloc}"
    if origin_from_public_url not in CORS_ALLOWED_ORIGINS:
         CORS_ALLOWED_ORIGINS.append(origin_from_public_url)

# --- Configuración de CSRF ---
CSRF_TRUSTED_ORIGINS_STRING = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS')
if CSRF_TRUSTED_ORIGINS_STRING:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STRING.split(',') if origin.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []
    if PUBLIC_URL_BASE and PUBLIC_URL_BASE.startswith('https://'):
        parsed_public_url = urlparse(PUBLIC_URL_BASE)
        origin_from_public_url = f"{parsed_public_url.scheme}://{parsed_public_url.netloc}"
        CSRF_TRUSTED_ORIGINS.append(origin_from_public_url)
    
    # Añadir hosts de ALLOWED_HOSTS que sean dominios (no IP/localhost) como https
    for host_str in ALLOWED_HOSTS:
        if host_str not in ['localhost', '127.0.0.1'] and '.' in host_str: # Asumir que es un dominio
            potential_origin = f"https://{host_str}"
            if potential_origin not in CSRF_TRUSTED_ORIGINS:
                 CSRF_TRUSTED_ORIGINS.append(potential_origin)
    
    if DEBUG:
        CSRF_TRUSTED_ORIGINS.extend(['http://localhost:8000', 'http://127.0.0.1:8000'])
    
    CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS))


# --- Logging ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {name} {module} {process:d} {thread:d} {message}', 'style': '{',},
    },
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose',},},
    'root': {'handlers': ['console'], 'level': 'INFO',},
    'loggers': {
        'django': {'handlers': ['console'], 'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'), 'propagate': False,},
        # Ya no necesitamos logs detallados de boto3, botocore, storages si no los usamos
        # 'boto3': { 'handlers': ['console'], 'level': 'WARNING','propagate': True,},
        # 'botocore': { 'handlers': ['console'], 'level': 'WARNING','propagate': True,},
        # 'storages': { 'handlers': ['console'], 'level': 'INFO','propagate': True,},
        'payments': {'handlers': ['console'],'level': 'DEBUG','propagate': False,},
        'blog': {'handlers': ['console'],'level': 'DEBUG','propagate': False,},
        'products': {'handlers': ['console'],'level': 'DEBUG','propagate': False,},
    },
}