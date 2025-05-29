from django.contrib import admin
from .models import Product # Asegúrate que .models apunte al lugar correcto

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_name', 'price', 'stock', 'is_active', 'updated_at')
    list_filter = ('is_active', 'category_name', 'updated_at')
    search_fields = ('name', 'description', 'category_name')
    prepopulated_fields = {'slug': ('name',)} # Ayuda a generar el slug automáticamente
    list_editable = ('price', 'stock', 'is_active')