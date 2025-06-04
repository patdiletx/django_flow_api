from django.contrib import admin
from .models import Tag, BlogPost
import logging

logger = logging.getLogger(__name__)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'author_name', 'date', 'is_published', 'updated_at')
    list_filter = ('is_published', 'date', 'tags', 'author_name')
    search_fields = ('title', 'excerpt', 'content', 'author_name')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    date_hierarchy = 'date'

    def save_model(self, request, obj, form, change):
        logger.debug(f"Attempting to save BlogPost: {obj.title}, User: {request.user.username}")
        super().save_model(request, obj, form, change)
        logger.info(f"BlogPost saved: {obj.title}")
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author_name')
        }),
        ('Publicación', {
            'fields': ('date', 'is_published', 'tags')
        }),
        ('Contenido Principal', {
            'fields': ('excerpt', 'content')
        }),
        ('Media', {
            'fields': (
                'image_url', # Este es el ImageField para la imagen principal
                'image_alt', 
                'data_ai_hint',
                'additional_image_urls', # Campo JSON
                'video_urls'             # Campo JSON
            ),
            'description': """
                <p>Para <strong>URLs de Imágenes Adicionales</strong> y <strong>URLs de Videos</strong>, ingrese una lista JSON válida.</p>
                <p>Ejemplo para imágenes: <code>["https://ejemplo.com/img1.jpg", "https://ejemplo.com/img2.png"]</code></p>
                <p>Ejemplo para videos: <code>["https://www.youtube.com/watch?v=VIDEO_ID", "https://vimeo.com/VIDEO_ID"]</code></p>
                <p>Si no hay, puede dejar el valor como <code>null</code> o un array vacío <code>[]</code> (algunas bases de datos prefieren null, otras el array vacío por defecto para JSONField si así se definió en el modelo).</p>
            """
        }),
    )