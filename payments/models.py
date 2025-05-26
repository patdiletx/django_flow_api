# payments/models.py

from django.db import models

class Order(models.Model):
    """
    Representa una orden de compra en nuestra base de datos.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PAID', 'Pagada'),
        ('REJECTED', 'Rechazada'),
    ]

    # Nuestro ID de orden interna. Debe ser único.
    commerce_order = models.CharField(max_length=100, unique=True)
    
    # El monto de la orden.
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # El estado actual de la orden.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    # El token que nos devuelve Flow para esta orden.
    flow_token = models.CharField(max_length=255, blank=True, null=True)
    
    # Campos de fecha y hora que se actualizan automáticamente.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Orden {self.commerce_order} - {self.get_status_display()}"