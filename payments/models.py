# payments/models.py

from django.db import models

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PAID', 'Pagada'),
        ('REJECTED', 'Rechazada'),
        ('ERROR', 'Error Interno'), # Podríamos añadir un estado de error nuestro
    ]

    commerce_order = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    flow_token = models.CharField(max_length=255, blank=True, null=True)
    
    # URL a la que FungiGrow quiere que el usuario sea redirigido finalmente
    fungigrow_return_url = models.URLField(max_length=500, blank=True, null=True)

    # Nuevos campos para detalles de envío
    shipping_name = models.CharField(max_length=255, blank=True, null=True)
    shipping_rut = models.CharField(max_length=20, blank=True, null=True) # RUT es específico de Chile
    shipping_address = models.CharField(max_length=500, blank=True, null=True)
    shipping_commune = models.CharField(max_length=100, blank=True, null=True)
    shipping_region = models.CharField(max_length=100, blank=True, null=True)
    shipping_phone = models.CharField(max_length=20, blank=True, null=True)
    
    customer_email = models.EmailField(max_length=254, blank=True, null=True) # Email del cliente

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Orden {self.commerce_order} - {self.get_status_display()}"