# products/serializers.py
from rest_framework import serializers
from .models import Product # O from payments.models import Product si está allí

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'slug', 
            'description', 
            'price', 
            'stock', 
            'image_url', 
            'category_name', 
            'is_active',
            'created_at',
            'updated_at'
        ]
        # Puedes usar '__all__' si quieres todos los campos, 
        # pero es buena práctica listar los que necesitas.
        # fields = '__all__'