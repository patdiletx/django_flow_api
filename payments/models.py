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
    applied_discount_code = models.CharField(max_length=50, null=True, blank=True, verbose_name="Código de Descuento Aplicado")

    customer_email = models.EmailField(max_length=254, blank=True, null=True) # Email del cliente

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Orden {self.commerce_order} - {self.get_status_display()}"




class DiscountCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Porcentaje'),
        ('fixed_amount', 'Monto Fijo'),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Código de Descuento")
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, verbose_name="Tipo de Descuento")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor del Descuento")
    is_active = models.BooleanField(default=True, verbose_name="¿Está Activo?")
    valid_from = models.DateTimeField(null=True, blank=True, verbose_name="Válido Desde")
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name="Válido Hasta")
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Monto Mínimo de Compra (subtotal productos)")
    usage_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name="Límite de Usos Totales")
    times_used = models.PositiveIntegerField(default=0, verbose_name="Veces Usado")
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto Máximo de Descuento (para porcentaje)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    def is_valid(self, cart_subtotal=None):
        if not self.is_active:
            return False, "Este código de descuento no está activo."
        
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False, "Este código de descuento aún no es válido."
        if self.valid_until and now > self.valid_until:
            return False, "Este código de descuento ha expirado."
        
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False, "Este código de descuento ha alcanzado su límite de usos."
            
        if cart_subtotal is not None and cart_subtotal < self.min_purchase_amount:
            return False, f"Esta compra no alcanza el monto mínimo de ${self.min_purchase_amount:,.0f} para usar este código."
            
        return True, "Código válido."

    def calculate_discount(self, amount):
        if self.discount_type == 'percentage':
            discount = (self.discount_value / 100) * amount
            if self.max_discount_amount is not None and discount > self.max_discount_amount:
                return self.max_discount_amount
            return discount
        elif self.discount_type == 'fixed_amount':
            # El descuento no puede ser mayor que el monto
            return min(self.discount_value, amount) 
        return 0