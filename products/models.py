# En products/models.py o payments/models.py

from django.db import models

class Product(models.Model):
    # --- Campos existentes ---
    name = models.CharField(max_length=255, verbose_name="Nombre del Producto")
    slug = models.SlugField(max_length=255, unique=True, help_text="Versión amigable para URL del nombre, usualmente en minúsculas y con guiones.")
    description = models.TextField(verbose_name="Descripción", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Precio") # Ajustado para CLP sin decimales
    stock = models.PositiveIntegerField(default=0, verbose_name="Cantidad en Stock")
    image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="URL de la Imagen")
    category_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre de Categoría")
    is_active = models.BooleanField(default=True, verbose_name="¿Está Activo?")
    
    # --- NUEVOS CAMPOS CRÍTICOS / ALTAMENTE RECOMENDADOS ---
    weight = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Peso (gramos)", 
        help_text="Peso del producto en GRAMOS. Esencial para cálculo de envío."
    )
    status_frontend = models.CharField(
        max_length=100, null=True, blank=True, 
        verbose_name="Estado para Frontend", 
        help_text="Ej: 'Listo para Fructificar (Cosecha Rápida)', 'Inicia Colonización en Casa (Ahorro)'"
    )
    lead_time_frontend = models.TextField(
        null=True, blank=True, verbose_name="Tiempo de Espera/Proceso Cliente", 
        help_text="Descripción del proceso en casa del cliente si aplica (ej. para kits de colonización)."
    )
    
    # --- NUEVOS CAMPOS OPCIONALES (Mejoran la experiencia en el frontend) ---
    harvest_time_frontend = models.CharField(
        max_length=50, null=True, blank=True, 
        verbose_name="Tiempo Estimado de Cosecha", 
        help_text="Ej: '7-12 días' o '1-2 semanas (después de colonización)'"
    )
    difficulty_frontend = models.CharField(
        max_length=50, null=True, blank=True, 
        verbose_name="Nivel de Dificultad", 
        help_text="Ej: 'Fácil', 'Medio', 'Avanzado'"
    )
    rating_frontend = models.FloatField(
        null=True, blank=True, verbose_name="Calificación Promedio"
    ) # O DecimalField(max_digits=2, decimal_places=1, ...)
    image_alt_frontend = models.CharField(
        max_length=255, null=True, blank=True, 
        verbose_name="Texto Alternativo de Imagen"
    )
    data_ai_hint_frontend = models.CharField(
        max_length=255, null=True, blank=True, 
        verbose_name="Palabras Clave para Búsqueda IA"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['name']

    def __str__(self):
        return self.name