from django.contrib import admin
from .models import Item, Collection, BorrowRequest  # Add other models as needed

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'location']  # Customize display fields

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_public']


@admin.register(BorrowRequest)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['message']