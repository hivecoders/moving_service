from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/customer/', views.register_customer, name='register_customer'),
    path('register/mover/', views.register_mover, name='register_mover'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/mover/', views.mover_dashboard, name='mover_dashboard'),
    path('create_order/', views.create_order, name='create_order'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('nearest_movers/<int:order_id>/', views.nearest_movers, name='nearest_movers'),
    path('order_details/<int:order_id>/', views.order_details, name='order_details'),

    # Payment URLs
    path('process_payment/<int:order_id>/', views.process_payment, name='process_payment'),
    path('payment_success/', views.home, name='payment_success'),  # Redirect to home after payment success
    path('payment_cancel/', views.home, name='payment_cancel'),    # Redirect to home if payment is canceled

    # Stripe webhook
    path('stripe_webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('logout/', views.logout_view, name='logout'), 

    # Accept and Reject Order URLs
    path('accept_order/<int:order_id>/', views.accept_order, name='accept_order'),
    path('reject_order/<int:order_id>/', views.reject_order, name='reject_order'),
]
