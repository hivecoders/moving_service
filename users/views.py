from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from geopy.distance import geodesic
from ultralytics import YOLO
import stripe
from .models import Customer, Mover, Order, DetectedItem, Photo, CustomUser
from utils.volume_weight_estimates import VOLUME_WEIGHT_ESTIMATES
from django.contrib.auth.decorators import login_required
from .forms import (
    MoverRegistrationForm, CustomerRegistrationForm, CustomUserLoginForm, 
    OrderForm, PhotoFormSet, MoverProfileForm, CustomerProfileForm, PhotoUploadForm
)

# Load YOLO model
yolo_model = YOLO("yolov8l.pt")

# Stripe Configuration
stripe.api_key = settings.STRIPE_SECRET_KEY

# Home Page View
def home(request):
    return render(request, 'users/home.html')

# User Authentication & Signup
def login_view(request):
    if request.method == 'POST':
        form = CustomUserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username').lower()
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                request.session.save()

                if hasattr(user, 'customer'):
                    return redirect('customer_dashboard')
                elif hasattr(user, 'mover'):
                    return redirect('mover_dashboard')
                else:
                    return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    
    else:
        form = CustomUserLoginForm()

    return render(request, 'registration/login.html', {'form': form})

# Customer Registration
def register_customer(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=True)
            Customer.objects.create(
                user=user,
                phone=form.cleaned_data.get('phone'),
                profile_photo=form.cleaned_data.get('profile_photo')
            )
            login(request, user)
            request.session.save()
            messages.success(request, "Account created successfully!")
            return redirect('customer_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerRegistrationForm()
    return render(request, 'users/register_customer.html', {'form': form})

# Mover Registration
def register_mover(request):
    if request.method == 'POST':
        form = MoverRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=True)
            mover = Mover.objects.create(
                user=user,
                phone=form.cleaned_data.get('phone'),
                vehicle_type=form.cleaned_data.get('vehicle_type') if form.cleaned_data.get('has_vehicle') == 'Yes' else None,
                mover_type=form.cleaned_data.get('mover_type'),
                location=request.POST.get('location_map'),
                payment_info=form.cleaned_data.get('payment_info'),
                driving_license=form.cleaned_data.get('driving_license') if form.cleaned_data.get('has_vehicle') == 'Yes' else None,
                carrying_capacity=form.cleaned_data.get('carrying_capacity') if form.cleaned_data.get('has_vehicle') == 'Yes' else None,
                has_mover_certification=request.POST.get('has_mover_certification') == 'on',
                mover_certification_document=request.FILES.get('mover_certification_document') if request.POST.get('has_mover_certification') == 'on' else None
            )
            login(request, user)
            request.session.save()
            messages.success(request, "Account created successfully!")
            return redirect('mover_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MoverRegistrationForm()
    return render(request, 'users/register_mover.html', {'form': form})

# Logout View
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')

# Order Creation
@login_required
def create_order(request):
    if request.method == 'POST':
        order_form = OrderForm(request.POST)
        photo_form = PhotoUploadForm(request.POST, request.FILES)
        if order_form.is_valid() and photo_form.is_valid():
            order = order_form.save()
            photo = photo_form.save(commit=False)
            photo.order = order
            photo.save()
            detect_objects(photo.image.path, order)
            messages.success(request, "Order successfully created!")
            return redirect('customer_dashboard')
    else:
        order_form = OrderForm()
        photo_form = PhotoUploadForm()
    return render(request, 'users/create_order.html', {'order_form': order_form, 'photo_form': photo_form})

def detect_objects(image_path, order):
    results = yolo_model(image_path)
    total_volume, total_weight = 0.0, 0.0

    for result in results:
        for box in result.boxes.data:
            item_name = result.names[int(box.cls.item())]
            confidence = float(box.conf.item())

            item_data = VOLUME_WEIGHT_ESTIMATES.get(item_name, {"volume": 0.5, "weight": 10.0})
            volume = item_data["volume"]
            weight = item_data["weight"]

            DetectedItem.objects.create(
                order=order,
                item_class=item_name,
                confidence=confidence,
                bbox={
                    'x1': float(box.xyxy[0].item()),
                    'y1': float(box.xyxy[1].item()),
                    'x2': float(box.xyxy[2].item()),
                    'y2': float(box.xyxy[3].item())
                },
                volume=volume,
                weight=weight
            )

            total_volume += volume
            total_weight += weight

    order.total_volume, order.total_weight = total_volume, total_weight
    order.save()

# Customer Dashboard
@login_required
def customer_dashboard(request):
    if hasattr(request.user, 'customer'):
        orders = Order.objects.filter(customer=request.user.customer)
        return render(request, 'users/customer_dashboard.html', {'orders': orders})
    else:
        messages.error(request, "Access denied.")
        return redirect('home')

# Mover Dashboard
@login_required
def mover_dashboard(request):
    if hasattr(request.user, 'mover'):
        orders = Order.objects.filter(items_detected__isnull=False).distinct()
        return render(request, 'users/mover_dashboard.html', {'orders': orders})
    else:
        messages.error(request, "Access denied.")
        return redirect('home')

# Accept or Reject Orders
@login_required
def accept_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Accepted'
    order.save()
    messages.success(request, "Order accepted successfully!")
    return redirect('mover_dashboard')

@login_required
def reject_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Rejected'
    order.save()
    messages.success(request, "Order rejected successfully!")
    return redirect('mover_dashboard')


# Order Details View
@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'users/order_details.html', {'order': order})

# Movers & Proximity Logic
def nearest_movers(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    movers = Mover.objects.all()
    order_location = tuple(map(float, order.origin_location.split(",")))

    nearest_movers = []
    for mover in movers:
        mover_location = tuple(map(float, mover.location.split(",")))
        distance = geodesic(order_location, mover_location).kilometers
        nearest_movers.append((mover, distance))

    nearest_movers.sort(key=lambda x: x[1])
    return render(request, 'users/nearest_movers.html', {'nearest_movers': nearest_movers})

# Payment Processing Views
def calculate_total_price(order):
    base_price = 100
    pro_mover_fee = 50 if order.need_pro_mover else 0
    box_packer_fee = 30 if order.need_box_packer else 0
    total_price = base_price + pro_mover_fee + box_packer_fee
    return total_price * 1.20

def process_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    amount = calculate_total_price(order)

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': f'Moving Order #{order.id}'},
                'unit_amount': int(amount * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/payment_success/'),
        cancel_url=request.build_absolute_uri('/payment_cancel/'),
    )

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Then define and call a method to handle the successful payment intent.
        handle_payment_intent_succeeded(payment_intent)
    # ... handle other event types

    return HttpResponse(status=200)

def handle_payment_intent_succeeded(payment_intent):
    # Fulfill the purchase...
    print("PaymentIntent was successful!")

@login_required
def edit_profile(request):
    if hasattr(request.user, 'mover'):
        if request.method == 'POST':
            form = MoverProfileForm(request.POST, request.FILES, instance=request.user.mover)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('mover_dashboard')
        else:
            form = MoverProfileForm(instance=request.user.mover)
    elif hasattr(request.user, 'customer'):
        if request.method == 'POST':
            form = CustomerProfileForm(request.POST, request.FILES, instance=request.user.customer)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('customer_dashboard')
        else:
            form = CustomerProfileForm(instance=request.user.customer)
    else:
        return redirect('home')

    return render(request, 'users/edit_profile.html', {'form': form})

