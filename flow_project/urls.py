# flow_project/urls.py

from django.contrib import admin
from django.urls import path, include
# Estas importaciones deben coincidir con dónde realmente tienes definidas estas vistas.
# Asumimos que ambas están en payments/views.py según nuestras últimas discusiones.
from payments.views import health_check_view, FlowCallbackView 

# Para servir archivos media en desarrollo (DEBUG=True) y si NO usas S3 localmente
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Ruta raíz para el health check (buena práctica para Render/plataformas)
    path('', health_check_view, name='health_check'),
    
    # Rutas del panel de administración de Django
    path('admin/', admin.site.urls),
    
    # Incluye todas las URLs del API de la app 'payments' bajo el prefijo /api/
    # Aquí deberían estar: /api/create-payment/, /api/validate-discount/, 
    # /api/order-status-by-token/, y el webhook /api/confirm-payment/
    path('api/', include('payments.urls')), 

    # Incluye todas las URLs del API de la app 'products' bajo el prefijo /api/products/
    # Aquí deberían estar: /api/products/ y /api/products/<slug>/
    path('api/products/', include('products.urls', namespace='products-api')),
    
    # Incluye todas las URLs del API de la app 'blog' bajo el prefijo /api/blog/
    # Aquí deberían estar: /api/blog/posts/ y /api/blog/posts/<slug>/
    path('api/blog/', include('blog.urls', namespace='blog-api')),
    
    # --- RUTA para el callback de Flow (urlReturn para Flow) ---
    # Esta es la URL a la que el navegador del usuario es redirigido DESDE Flow,
    # manejada por nuestra FlowCallbackView.
    path('payment/flow-callback/', FlowCallbackView.as_view(), name='flow-callback'),
]

# --- SERVICIO DE ARCHIVOS MEDIA EN DESARROLLO ---
# Esto es para que el servidor de desarrollo de Django sirva los archivos
# que subes a MEDIA_ROOT cuando DEBUG = True y NO estás usando S3 como
# DEFAULT_FILE_STORAGE. En producción con DEBUG = False, Render o S3
# se encargarán de servir estos archivos.
if settings.DEBUG and not getattr(settings, 'USING_S3', False): # getattr para evitar AttributeError si USING_S3 no existe
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)