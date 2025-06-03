from django.db import models
from django.utils.text import slugify
from django.conf import settings # Para el autor por defecto o FK a User

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Tag")
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="Versión amigable para URL del nombre del tag.")

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class BlogPost(models.Model):
    title = models.CharField(max_length=255, verbose_name="Título")
    slug = models.SlugField(max_length=270, unique=True, db_index=True, help_text="Identificador único para la URL (se genera automáticamente si se deja vacío).")
    date = models.DateTimeField(verbose_name="Fecha de Publicación") # Usamos DateTimeField para más precisión, pero se puede formatear como fecha
    
    # Opción 1: Autor como CharField simple
    author_name = models.CharField(max_length=150, verbose_name="Nombre del Autor")
    # Opción 2: Autor como ForeignKey al modelo User de Django (si tienes sistema de usuarios)
    # author_user = models.ForeignKey(
    #     settings.AUTH_USER_MODEL, 
    #     on_delete=models.SET_NULL, # O models.PROTECT, etc.
    #     null=True, blank=True, 
    #     verbose_name="Autor (Usuario)"
    # )
    
    excerpt = models.TextField(verbose_name="Resumen Corto")
    content = models.TextField(verbose_name="Contenido Completo (HTML)") # Se asume que el frontend manejará el renderizado de HTML
    
    image_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="URL de Imagen Principal")
    image_alt = models.CharField(max_length=255, null=True, blank=True, verbose_name="Texto Alternativo de Imagen Principal")
    data_ai_hint = models.CharField(max_length=255, null=True, blank=True, verbose_name="Palabras Clave para IA (Imagen)")
    
    tags = models.ManyToManyField(Tag, blank=True, related_name="blog_posts", verbose_name="Tags")
    
    is_published = models.BooleanField(default=True, db_index=True, verbose_name="¿Está Publicado?")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Artículo del Blog"
        verbose_name_plural = "Artículos del Blog"
        ordering = ['-date'] # Ordenar por fecha de publicación descendente

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Asegurar unicidad del slug si se autogenera
            original_slug = self.slug
            counter = 1
            while BlogPost.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title