# En products/models.py o payments/models.py

from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Producto")
    slug = models.SlugField(max_length=255, unique=True, help_text="Versión amigable para URL del nombre, usualmente en minúsculas y con guiones.")
    description = models.TextField(verbose_name="Descripción", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Precio") # Asume 2 decimales, ajusta si es CLP sin decimales
    stock = models.PositiveIntegerField(default=0, verbose_name="Cantidad en Stock")
    # Para la imagen, la forma más simple es un campo URL. 
    # Si quieres subir imágenes, se usa ImageField y requiere más configuración (Pillow, MEDIA_ROOT, MEDIA_URL).
    image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="URL de la Imagen")
    category_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre de Categoría") # Simple por ahora
    is_active = models.BooleanField(default=True, verbose_name="¿Está Activo?") # Para mostrar/ocultar el producto
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['name']

    def __str__(self):
        return self.name