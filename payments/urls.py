# payments/urls.py

from django.urls import path
# Asegúrate de que TODAS las vistas que usas en este archivo estén importadas aquí
from .views import (
    CreatePaymentView, 
    FlowConfirmationView,
    OrderStatusView,
    GetOrderStatusByTokenView,
    QueryOrderStatusView 
)

urlpatterns = [
    path('create-payment/', CreatePaymentView.as_view(), name='create-payment'),
    path('confirm-payment/', FlowConfirmationView.as_view(), name='flow-confirmation'),
    path('order-status-by-token/<str:flow_token>/', GetOrderStatusByTokenView.as_view(), name='order-status-by-token'),
    path('query-order-status/', QueryOrderStatusView.as_view(), name='query-order-status'),
]