# products/admin.py (o payments/admin.py)
from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_name', 'price', 'stock', 'weight', 'status_frontend', 'is_active', 'updated_at')
    list_filter = ('is_active', 'category_name', 'status_frontend', 'difficulty_frontend', 'updated_at')
    search_fields = ('name', 'description', 'category_name', 'status_frontend')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('price', 'stock', 'weight', 'status_frontend', 'is_active')
    
    # Para una mejor organización en el formulario de edición, puedes usar fieldsets:
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'is_active', 'category_name')
        }),
        ('Descripción y Contenido', {
            'fields': ('description', 'image_url', 'image_alt_frontend')
        }),
        ('Media Adicional (Imágenes y Videos)', {
            'fields': ('additional_image_urls', 'video_urls'),
            'description': """
                <p>Para <strong>URLs de Imágenes Adicionales</strong> y <strong>URLs de Videos</strong>, ingrese una lista JSON válida.</p>
                <p>Ejemplo para imágenes: <code>["https://ejemplo.com/img1.jpg", "https://ejemplo.com/img2.png"]</code></p>
                <p>Ejemplo para videos: <code>["https://www.youtube.com/watch?v=VIDEO_ID", "https://vimeo.com/VIDEO_ID"]</code></p>
                <p>Si no hay, deje como <code>null</code> o <code>[]</code>.</p>
            """
        }),
        ('Precio y Stock', {
            'fields': ('price', 'stock', 'weight')
        }),
        ('Detalles para Frontend FungiGrow', {
            'fields': ('status_frontend', 'lead_time_frontend', 'harvest_time_frontend', 'difficulty_frontend', 'rating_frontend')
        }),
        ('Datos para IA (Opcional)', {
            'fields': ('data_ai_hint_frontend',),
            'classes': ('collapse',) # Para que aparezca colapsado
        }),
    )