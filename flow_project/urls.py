# flow_project/urls.py

from django.contrib import admin
from django.urls import path, include
# --- ASEGÚRATE DE QUE ESTA LÍNEA ESTÉ AQUÍ ---
from payments.views import PaymentResultView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('payments.urls')), # Rutas para nuestro API interno

    # Ruta para la página que ve el usuario al volver de Flow
    path('payment/result/<str:commerce_order>/', PaymentResultView.as_view(), name='payment-result-page'),
]