"""
Django settings for flow_project project.
"""
import os
from pathlib import Path
from urllib.parse import urlparse # Para CSRF_TRUSTED_ORIGINS

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Clave Secreta ---
# ¡IMPORTANTE! En producción, esta clave DEBE estar en tus variables de entorno.
# Genera una nueva con: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'una-clave-secreta-por-defecto-solo-para-desarrollo-local')

# --- Modo Debug ---
# En producción (Render), esta variable de entorno DJANGO_DEBUG debe ser 'False'.
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# --- Hosts Permitidos ---
# En Render, configura DJANGO_ALLOWED_HOSTS con tu dominio de Render, ej: "django-flow-api.onrender.com,www.tudominio.com"
ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]


# --- URLs Base Configurables desde el Entorno ---
# URL pública de este backend API (ej: https://django-flow-api.onrender.com)
PUBLIC_URL_BASE = os.getenv('PUBLIC_URL_BASE', f"http://localhost:8000")
# URL base de la tienda frontend FungiGrow (ej: https://www.fungigrow.com)
FUNGIFRESH_STORE_URL = os.getenv('FUNGIFRESH_STORE_URL', 'http://localhost:3000')


# --- Application definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles', # Necesario para el admin y whitenoise
    
    # Apps de Terceros
    'rest_framework',
    'corsheaders',
    'storages', # Para django-storages (S3)
    
    # Mis Apps
    'payments.apps.PaymentsConfig', # Usando la configuración explícita de la app
    'products.apps.ProductsConfig', # Si tienes app 'products'
    'blog.apps.BlogConfig',         # Si tienes app 'blog'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Debe ir después de SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',      # Usualmente antes de CommonMiddleware
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
        'DIRS': [BASE_DIR / 'templates'], # Usando pathlib para construir la ruta
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug', # Necesario para que DEBUG funcione en plantillas
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'flow_project.wsgi.application'


# --- Base de Datos ---
# Configuración para SQLite persistente en Render o local
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
EMAIL_PORT = int(EMAIL_PORT_STR) if EMAIL_PORT_STR.isdigit() else 587
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com') # Cambia example.com
STORE_OWNER_EMAIL = os.getenv('STORE_OWNER_EMAIL') # Obligatorio en entorno para notificaciones

# --- Configuración de n8n ---
N8N_SALE_WEBHOOK_URL = os.getenv('N8N_SALE_WEBHOOK_URL')

# --- Configuración de AWS S3 para Archivos Media ---
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', None)
AWS_LOCATION = os.getenv('AWS_LOCATION', 'media') # Subcarpeta en S3

USING_S3 = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME and AWS_S3_REGION_NAME)

if USING_S3:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None 
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_VERIFY = True
    
    if AWS_S3_ENDPOINT_URL: # Para S3 compatibles
        MEDIA_URL = f'{AWS_S3_ENDPOINT_URL.rstrip("/")}/{AWS_LOCATION}/'
    else: # Para AWS S3 estándar
        MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/{AWS_LOCATION}/'
    
    MEDIA_ROOT = BASE_DIR / 'mediafiles_s3_placeholder_not_actively_used' # No se usa para guardar en S3
else:
    # Desarrollo local sin S3 (archivos en disco)
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'mediafiles'
    if not MEDIA_ROOT.exists(): # Usar .exists() para pathlib.Path
        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# --- Archivos Estáticos (CSS, JavaScript, Imágenes de la app/admin) ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # Carpeta para 'collectstatic'
# Para Whitenoise en producción (recomendado si no usas un CDN dedicado para estáticos)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'es-cl' # Ajustado a Chile
TIME_ZONE = 'America/Santiago' # Ajustado a Chile
USE_I18N = True
USE_TZ = True # Recomendado para manejar zonas horarias correctamente

# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Configuración de CORS ---
# Lee los orígenes permitidos de una variable de entorno, separados por coma
CORS_ALLOWED_ORIGINS_STRING = os.getenv('DJANGO_CORS_ALLOWED_ORIGINS')
if CORS_ALLOWED_ORIGINS_STRING:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS_STRING.split(',') if origin.strip()]
else:
    # Defaults para desarrollo local si la variable no está definida
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000", # Puerto común para React/Vue/Next.js local
        "http://127.0.0.1:3000",
        "http://localhost:8080", # Otro puerto común
        "http://127.0.0.1:8080",
    ]

# Si tu PUBLIC_URL_BASE es un origen de confianza y no está en la lista, añádelo
if PUBLIC_URL_BASE and PUBLIC_URL_BASE not in CORS_ALLOWED_ORIGINS:
    # Extraer solo el scheme://hostname:port
    parsed_public_url = urlparse(PUBLIC_URL_BASE)
    origin_from_public_url = f"{parsed_public_url.scheme}://{parsed_public_url.netloc}"
    if origin_from_public_url not in CORS_ALLOWED_ORIGINS:
         CORS_ALLOWED_ORIGINS.append(origin_from_public_url)

# Para CSRF, necesitamos confiar en los orígenes HTTPS desde donde se pueden hacer POST
# (como tu dominio de Render o el dominio de FungiGrow si el admin se accediera desde allí).
CSRF_TRUSTED_ORIGINS_STRING = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS')
if CSRF_TRUSTED_ORIGINS_STRING:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STRING.split(',') if origin.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []
    # Derivar de ALLOWED_HOSTS o PUBLIC_URL_BASE para HTTPS
    if PUBLIC_URL_BASE and PUBLIC_URL_BASE.startswith('https://'):
        parsed_public_url = urlparse(PUBLIC_URL_BASE)
        origin_from_public_url = f"{parsed_public_url.scheme}://{parsed_public_url.netloc}"
        CSRF_TRUSTED_ORIGINS.append(origin_from_public_url)
    
    for host in ALLOWED_HOSTS: # Añadir hosts de ALLOWED_HOSTS si son https
        if host not in ['localhost', '127.0.0.1'] and not host.startswith('http'):
            CSRF_TRUSTED_ORIGINS.append(f"https://{host}")

    # Asegurar que no haya duplicados
    CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS))
    
    # Si después de todo sigue vacío y estamos en debug, añadir localhost para el admin
    if not CSRF_TRUSTED_ORIGINS and DEBUG:
        CSRF_TRUSTED_ORIGINS.extend(['http://localhost:8000', 'http://127.0.0.1:8000'])


# --- Logging ---
# (Tu configuración de LOGGING que ya tenías está bien si te funciona,
#  asegúrate que 'import os' esté al principio para os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'))
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': { # Captura logs de todo si no tienen un logger específico
        'handlers': ['console'],
        'level': 'DEBUG', # Ponemos DEBUG en root para capturar todo
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'), # Puedes subirlo a DEBUG también
            'propagate': False, # Evita que los logs de django se dupliquen en root
        },
        'boto3': { # Para la librería de AWS
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True, # Permite que también los vea el root logger
        },
        'botocore': { # Usado por boto3
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'storages': { # Para django-storages
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        # Tus apps, ponlas en DEBUG si quieres ver sus logger.debug()
        'payments': {'handlers': ['console'],'level': 'DEBUG','propagate': True,},
        'blog': {'handlers': ['console'],'level': 'DEBUG','propagate': True,},
        'products': {'handlers': ['console'],'level': 'DEBUG','propagate': True,},
    },
}