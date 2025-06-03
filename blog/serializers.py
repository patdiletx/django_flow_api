# blog/serializers.py
from rest_framework import serializers
from .models import Tag, BlogPost

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'slug']

class BlogPostListSerializer(serializers.ModelSerializer):
    # Para devolver los tags como una lista de strings (nombres)
    tags = serializers.StringRelatedField(many=True)
    # Formatear la fecha a ISO 8601 (solo fecha o fecha y hora)
    # DRF DateTimeField por defecto usa ISO 8601, pero podemos ser explícitos o ajustarlo
    date = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True) # Formato con hora UTC
    # Si solo quieres la fecha: date = serializers.DateField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            'id', 'slug', 'title', 'date', 'author_name', # Usa author_user.username si es ForeignKey
            'excerpt', 'image_url', 'image_alt', 'data_ai_hint', 'tags'
        ]

class BlogPostDetailSerializer(serializers.ModelSerializer):
    tags = serializers.StringRelatedField(many=True)
    date = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    # Si usas ForeignKey para autor:
    # author_name = serializers.CharField(source='author_user.get_full_name', read_only=True, default=None)
    # O si author_user puede ser null y quieres el author_name del modelo:
    # author_display = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id', 'slug', 'title', 'date', 'author_name', # O author_display
            'excerpt', 'content', # 'content' se incluye aquí
            'image_url', 'image_alt', 'data_ai_hint', 'tags',
            'created_at', 'updated_at' # Campos adicionales para el detalle
        ]
    
    # Ejemplo si necesitas combinar author_user y author_name:
    # def get_author_display(self, obj):
    #     if obj.author_user:
    #         return obj.author_user.get_full_name() or obj.author_user.username
    #     return obj.author_name