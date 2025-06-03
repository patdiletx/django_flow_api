from django.contrib import admin
from .models import Tag, BlogPost

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
    filter_horizontal = ('tags',) # Mejor UI para ManyToManyField
    date_hierarchy = 'date'
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author_name') # Reemplaza author_name por author_user si usas ForeignKey
        }),
        ('Publicación', {
            'fields': ('date', 'is_published', 'tags')
        }),
        ('Contenido Principal', {
            'fields': ('excerpt', 'content')
        }),
        ('Media', {
            'fields': ('image', 'image_alt', 'data_ai_hint', 'additional_image_urls', 'video_urls')
        }),
    )