# flow_project/urls.py

from django.contrib import admin
from django.urls import path, include

# --- IMPORTA PaymentResultView Y health_check_view DESDE payments.views ---
from payments.views import PaymentResultView, health_check_view 

urlpatterns = [
    # La ruta raíz ahora usa la health_check_view importada
    path('', health_check_view, name='health_check'), 
    
    path('admin/', admin.site.urls),
    path('api/', include('payments.urls')), # Rutas para nuestro API interno
    
    path('payment/final-status/<str:commerce_order>/', PaymentFinalStatusView.as_view(), name='payment-final-status'),

    # Ruta para la página que ve el usuario al volver de Flow
    # path('payment/result/<str:commerce_order>/', PaymentResultView.as_view(), name='payment-result-page'),
]