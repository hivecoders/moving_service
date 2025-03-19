from django.urls import path
from . import views
from .views import (
    accept_order, reject_order, mark_order_as_done, confirm_mission_complete
)

urlpatterns = [
    # Home Page
    path('', views.home, name='home'),

    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Registration URLs
    path('register/customer/', views.register_customer, name='register_customer'),
    path('register/mover/', views.register_mover, name='register_mover'),

    # Dashboard URLs (Separate for Customer & Mover)
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/mover/', views.mover_dashboard, name='mover_dashboard'),

    # Order Related URLs
    path('remove_detected_item/<int:item_id>/', views.remove_detected_item, name='remove_detected_item'),
    path('create_order/', views.create_order, name='create_order'),
    path('create_order_step2/', views.create_order_step2, name='create_order_step2'), 
    path('order_details/<int:order_id>/', views.order_details, name='order_details'),
    path('nearest_movers/<int:order_id>/', views.nearest_movers, name='nearest_movers'),

    #  edit profile
    path('edit_profile/', views.edit_profile, name='edit_profile'),

    # Payment Processing
    path('process_payment/<int:order_id>/', views.process_payment, name='process_payment'),
    path('payment_success/', views.home, name='payment_success'),
    path('payment_cancel/', views.home, name='payment_cancel'),

    # Stripe Webhook
    path('stripe_webhook/', views.stripe_webhook, name='stripe_webhook'),

    # Order Management for Movers
    path('accept_order/<int:order_id>/', views.accept_order, name='accept_order'),
    path('reject_order/<int:order_id>/', views.reject_order, name='reject_order'),
    path('order/<int:order_id>/accept/', accept_order, name='accept_order'),
    path('order/<int:order_id>/reject/', reject_order, name='reject_order'),
    path('order/<int:order_id>/confirm_complete/', confirm_mission_complete, name='confirm_mission_complete'),
    path('order/<int:order_id>/mark_done/', mark_order_as_done, name='mark_order_as_done'),
    path('order/<int:order_id>/bid/', views.place_bid, name='place_bid'),
    path('order/<int:order_id>/confirm_complete/', confirm_mission_complete, name='confirm_mission_complete'),
    path('order/<int:order_id>/mark_done/', mark_order_as_done, name='mark_order_as_done'),
]
