from rest_framework import generics
from .models import BlogPost
from .serializers import BlogPostListSerializer, BlogPostDetailSerializer

class BlogPostListView(generics.ListAPIView):
    """
    Devuelve una lista de todos los artículos del blog publicados.
    Considera añadir paginación aquí si la lista es larga.
    """
    queryset = BlogPost.objects.filter(is_published=True).order_by('-date')
    serializer_class = BlogPostListSerializer
    # pagination_class = TuClaseDePaginacion (ej. PageNumberPagination)

class BlogPostDetailView(generics.RetrieveAPIView):
    """
    Devuelve los detalles de un artículo específico por su slug.
    Solo artículos publicados.
    """
    queryset = BlogPost.objects.filter(is_published=True)
    serializer_class = BlogPostDetailSerializer
    lookup_field = 'slug' # Para buscar por slug en la URL