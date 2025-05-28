# flow_project/urls.py
from django.contrib import admin
from django.urls import path, include
from payments.views import health_check_view, FlowCallbackView # <-- Añade FlowCallbackView

urlpatterns = [
    path('', health_check_view, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/', include('payments.urls')), 
    
    # --- RUTA para el callback de Flow (urlReturn para Flow) ---
    path('payment/flow-callback/', FlowCallbackView.as_view(), name='flow-callback'),
    # La antigua 'payment/final-status/' o 'payment/result/' ya no se necesita si esta la reemplaza
]