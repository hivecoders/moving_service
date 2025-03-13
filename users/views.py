import logging
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

logger = logging.getLogger(__name__)

# Load YOLO model
yolo_model = YOLO("yolov8l.pt")

# Stripe Configuration
stripe.api_key = settings.STRIPE_SECRET_KEY

# Home Page View
def home(request):
    logger.info("Rendering home page")
    return render(request, 'users/home.html')
# Order Creation
@login_required
def create_order(request):
    logger.info("Creating a new order (step 1)")
    if request.method == 'POST':
        order_form = OrderForm(request.POST)

        if order_form.is_valid():
            order = order_form.save(commit=False)
            order.customer = request.user.customer
            order.status = "Pending"
            
            order.has_elevator = request.POST.get('has_elevator') == 'on'
            order.need_pro_mover = request.POST.get('need_pro_mover') == 'on'
            order.need_box_packer = request.POST.get('need_box_packer') == 'on'
            order.save()

            request.session['order_id'] = order.id
            messages.success(request, "Order details saved. Proceed to upload photos.")
            logger.info(f"Order {order.id} created (step 1)")
            return redirect('create_order_step2')
        else:
            logger.error(f"Order creation failed: {order_form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        order_form = OrderForm()

    return render(request, 'users/create_order.html', {'order_form': order_form})

## **create_order_step2**
@login_required
def create_order_step2(request):
    order_id = request.session.get('order_id')

    if not order_id:
        messages.error(request, "No order found. Please create an order first.")
        return redirect('create_order')

    order = get_object_or_404(Order, id=order_id)
    detected_items = request.session.get('detected_items', [])

    if request.method == 'POST':
        selected_items = request.POST.getlist('selected_items')
        manual_items = request.POST.getlist('manual_items')
        vehicle_type = request.POST.get('vehicle_type')
        images = request.FILES.getlist('images')

        total_volume, total_weight = 0.0, 0.0

        # ذخیره تصاویر در مدل `Photo`
        for image in images:
            photo = Photo.objects.create(order=order, image=image)

            # پردازش تصویر با YOLO
            detected_objects = detect_objects(photo.image.path, order)

            # ذخیره اشیای تشخیص داده‌شده
            for obj in detected_objects:
                detected_item = DetectedItem.objects.create(
                    order=order,
                    item_class=obj["item"],
                    volume=obj["volume"],
                    weight=obj["weight"],
                    confidence=obj.get("confidence", 1.0)
                )
                total_volume += obj["volume"]
                total_weight += obj["weight"]

        
        for item in detected_items:
            if item['item'] in selected_items:
                DetectedItem.objects.create(
                    order=order,
                    item_class=item['item'],
                    volume=item['volume'],
                    weight=item['weight'],
                    confidence=1.0
                )
                total_volume += item['volume']
                total_weight += item['weight']

        for item in manual_items:
            DetectedItem.objects.create(
                order=order,
                item_class=item,
                volume=0,
                weight=0,
                confidence=1.0
            )

        order.total_volume = total_volume
        order.total_weight = total_weight
        order.vehicle_type = vehicle_type
        order.save()

        messages.success(request, "Order items added successfully!")
        logger.info(f"Order {order.id} updated (step 2)")
        return redirect('customer_dashboard')

    return render(request, 'users/create_order_step2.html', {'detected_items': detected_items})

# User Authentication & Signup
def login_view(request):
    logger.info("Login attempt")

    next_url = request.GET.get('next', '')
    
    if request.method == 'POST':
        form = CustomUserLoginForm(request, data=request.POST)


        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            if email:
                email = email.lower()  # to lower letter
                logger.debug(f"Authenticating user: {email}")

            # `username` to `email` change
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                request.session.save()
                logger.info(f"User {email} logged in successfully")

                if hasattr(user, 'customer'):
                    return redirect('customer_dashboard')
                elif hasattr(user, 'mover'):
                    return redirect('mover_dashboard')
                else:
                    return redirect('home')
            else:
                logger.warning(f"Invalid login attempt for {email}")
                messages.error(request, "Invalid email or password.")
        else:
            logger.error(f"Form validation failed: {form.errors}")
            messages.error(request, "Please correct the errors below.")

    else:
        form = CustomUserLoginForm()

    return render(request, 'registration/login.html', {'form': form, 'next': next_url})


# Customer Registration
def register_customer(request):
    logger.info("Customer registration attempt")
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
            logger.info(f"Customer {user.email} registered successfully")
            return redirect('customer_dashboard')
        else:
            logger.error(f"Customer registration failed: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerRegistrationForm()
    return render(request, 'users/register_customer.html', {'form': form})

# Mover Registration
def register_mover(request):
    logger.info("Mover registration attempt")
    if request.method == 'POST':
        form = MoverRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=True)
            Mover.objects.create(
                user=user,
                phone=form.cleaned_data.get('phone'),
                vehicle_type=form.cleaned_data.get('vehicle_type') if form.cleaned_data.get('has_vehicle') == 'Yes' else None,
                mover_type=form.cleaned_data.get('mover_type'),
                location=request.POST.get('location_map'),
                payment_info=form.cleaned_data.get('payment_info'),
                driving_license=form.cleaned_data.get('driving_license') if form.cleaned_data.get('has_vehicle') == 'Yes' else None,
                carrying_capacity=form.cleaned_data.get('carrying_capacity') if form.cleaned_data.get('has_vehicle') == 'Yes' else None
            )
            login(request, user)
            request.session.save()
            logger.info(f"Mover {user.email} registered successfully")
            return redirect('mover_dashboard')
        else:
            logger.error(f"Mover registration failed: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = MoverRegistrationForm()
    return render(request, 'users/register_mover.html', {'form': form})

# Logout View
def logout_view(request):
    logger.info(f"User {request.user.email} logged out")
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')



# Object Detection
def detect_objects(image_path, order):
    logger.info(f"Processing image for order {order.id}")
    results = yolo_model(image_path)
    detected_items = []

    for result in results:
        for box in result.boxes.data:
            item_name = result.names[int(box.cls.item())]
            confidence = float(box.conf.item())

            item_data = VOLUME_WEIGHT_ESTIMATES.get(item_name, {"volume": 0.5, "weight": 10.0})
            volume = item_data["volume"]
            weight = item_data["weight"]

            detected_item = DetectedItem.objects.create(
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

            detected_items.append({"item": item_name, "volume": volume, "weight": weight})

    return detected_items



# Customer Dashboard
@login_required
def customer_dashboard(request):
    logger.info("Accessing customer dashboard for user: %s", request.user)
    if hasattr(request.user, 'customer'):
        orders = Order.objects.filter(customer=request.user.customer)
        return render(request, 'users/customer_dashboard.html', {'orders': orders})
    else:
        messages.error(request, "Access denied.")
        return redirect('home')

# Mover Dashboard
@login_required
def mover_dashboard(request):
    logger.info("Accessing mover dashboard for user: %s", request.user)
    if hasattr(request.user, 'mover'):
        orders = Order.objects.filter(items_detected__isnull=False).distinct()
        return render(request, 'users/mover_dashboard.html', {'orders': orders})
    else:
        messages.error(request, "Access denied.")
        return redirect('home')

# Accept or Reject Orders
@login_required
def accept_order(request, order_id):
    logger.info("Accepting order: %s", order_id)
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Accepted'
    order.save()
    messages.success(request, "Order accepted successfully!")
    return redirect('mover_dashboard')

@login_required
def reject_order(request, order_id):
    logger.info("Rejecting order: %s", order_id)
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Rejected'
    order.save()
    messages.success(request, "Order rejected successfully!")
    return redirect('mover_dashboard')

# Order Details View
@login_required
def order_details(request, order_id):
    logger.info("Fetching order details for order: %s", order_id)
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'users/order_details.html', {'order': order})

# Movers & Proximity Logic
def nearest_movers(request, order_id):
    logger.info("Finding nearest movers for order: %s", order_id)
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
    logger.info("Calculating total price for order: %s", order.id)
    base_price = 100
    pro_mover_fee = 50 if order.need_pro_mover else 0
    box_packer_fee = 30 if order.need_box_packer else 0
    total_price = base_price + pro_mover_fee + box_packer_fee
    return total_price * 1.20

def process_payment(request, order_id):
    logger.info("Processing payment for order: %s", order_id)
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
        logger.error("Invalid payload in Stripe webhook.")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature in Stripe webhook.")
        return HttpResponse(status=400)

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_intent_succeeded(payment_intent)
    
    return HttpResponse(status=200)

def handle_payment_intent_succeeded(payment_intent):
    logger.info("PaymentIntent was successful!")

@login_required
def edit_profile(request):
    logger.info("Editing profile for user: %s", request.user)
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


