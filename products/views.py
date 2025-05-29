# products/views.py
from rest_framework import generics
from .models import Product # O from payments.models import Product
from .serializers import ProductSerializer

class ProductListView(generics.ListAPIView):
    """
    Vista para listar todos los productos activos.
    Permite peticiones GET.
    """
    queryset = Product.objects.filter(is_active=True).order_by('name')
    serializer_class = ProductSerializer
    # Aquí podrías añadir clases de paginación, filtros, etc. en el futuro


class ProductDetailView(generics.RetrieveAPIView):
    """
    Vista para obtener los detalles de un solo producto activo, usando su slug.
    Permite peticiones GET.
    """
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    lookup_field = 'slug' # Usaremos el slug para buscar el producto en la URL
                          # ej: /api/products/kit-cultivo-ostra-rosado/