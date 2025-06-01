# products/serializers.py (o payments/serializers.py)
from rest_framework import serializers
from .models import Product # O from payments.models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'stock', 
            'image_url', 'category_name', 'is_active',
            'created_at', 'updated_at',
            # --- NUEVOS CAMPOS ---
            'weight', 
            'status_frontend', 
            'lead_time_frontend',
            'harvest_time_frontend', 
            'difficulty_frontend', 
            'rating_frontend',
            'image_alt_frontend', 
            'data_ai_hint_frontend',
            'additional_image_urls',
            'video_urls'
        ]