from django.contrib import admin
from .models import Customer, Mover, Order, DetectedItem, Photo

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')  # یا 'user.name' بسته به نیاز
    search_fields = ['user__username', 'phone']  # اگر از 'user' برای نام استفاده می‌کنید

class MoverAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'vehicle_type', 'mover_type', 'location')
    search_fields = ['user__username', 'phone', 'vehicle_type', 'mover_type']

class OrderAdmin(admin.ModelAdmin):
    list_display = ('customer', 'origin', 'destination', 'move_date', 'need_pro_mover', 'need_box_packer')
    search_fields = ['origin', 'destination', 'customer__user__username']  # اگر به دنبال جستجو در نام کاربر هستید
    list_filter = ('move_date', 'need_pro_mover', 'need_box_packer')

class DetectedItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'item_class', 'confidence')
    search_fields = ['order__customer__user__username', 'item_class']

class PhotoAdmin(admin.ModelAdmin):
    list_display = ('order', 'image')
    search_fields = ['order__customer__user__username']

admin.site.register(Customer, CustomerAdmin)
admin.site.register(Mover, MoverAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(DetectedItem, DetectedItemAdmin)
admin.site.register(Photo, PhotoAdmin)
