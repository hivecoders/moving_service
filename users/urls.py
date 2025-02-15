from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/customer/', views.register_customer, name='register_customer'),
    path('register/mover/', views.register_mover, name='register_mover'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('mover_dashboard/', views.mover_dashboard, name='mover_dashboard'),
    path('create_order/', views.create_order, name='create_order'),
    path('nearest_movers/<int:order_id>/', views.nearest_movers, name='nearest_movers'),

    # Payment URLs
    path('process_payment/<int:order_id>/', views.process_payment, name='process_payment'),
    path('payment_success/', views.home, name='payment_success'),  # Redirect to home after payment success
    path('payment_cancel/', views.home, name='payment_cancel'),    # Redirect to home if payment is canceled

    # Stripe webhook
    path('stripe_webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('logout/', views.logout_view, name='logout'), 
]
