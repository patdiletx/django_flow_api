# payments/admin.py
from django.contrib import admin
from .models import Order, DiscountCode # Añade DiscountCode

# ... (Tu ProductAdmin y OrderAdmin existentes) ...

@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'valid_from', 'valid_until', 'min_purchase_amount', 'usage_limit', 'times_used')
    list_filter = ('is_active', 'discount_type', 'valid_from', 'valid_until')
    search_fields = ('code',)
    list_editable = ('is_active', 'discount_value', 'usage_limit')