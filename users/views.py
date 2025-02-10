from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from geopy.distance import geodesic
from ultralytics import YOLO
import stripe, json
from .models import Customer, Mover, Order, DetectedItem, Photo
from utils.volume_weight_estimates import VOLUME_WEIGHT_ESTIMATES
from django.contrib.auth.decorators import login_required
from .forms import MoverRegistrationForm, CustomerRegistrationForm, CustomUserLoginForm, OrderForm, PhotoFormSet


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
            username = form.cleaned_data.get('username') 
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                if hasattr(user, 'customer'):  
                    return redirect('dashboard')  
                elif hasattr(user, 'mover'):  
                    return redirect('mover_dashboard')  
            else:
                messages.error(request, "Incorrect username or password.")
    else:
        form = CustomUserLoginForm()
    return render(request, 'users/login.html', {'form': form})

# Customer Registration
def register_customer(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()  # Save User first
            customer = Customer.objects.create(
                user=user,
                full_name=form.cleaned_data.get('full_name'),  # Use full_name field
                phone=form.cleaned_data.get('phone')
            )
            login(request, user)  # Auto-login after registration
            messages.success(request, "Customer registration successful!")
            return redirect('dashboard')  # Redirect to dashboard after successful registration
        else:
            messages.error(request, "Please fill out all required fields.")
    else:
        form = CustomerRegistrationForm()

    return render(request, 'users/register_customer.html', {'form': form})

# Mover Registration
def register_mover(request):
    if request.method == 'POST':
        form = MoverRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()  
            mover = Mover.objects.create(
                user=user,
                full_name=form.cleaned_data.get('full_name'),
                phone=form.cleaned_data.get('phone'),
                vehicle_type=form.cleaned_data.get('vehicle_type'),
                mover_type=form.cleaned_data.get('mover_type'),
                location=form.cleaned_data.get('location'),
                payment_info=form.cleaned_data.get('payment_info')
            )
            login(request, user)  # Auto-login after registration
            messages.success(request, "Account created successfully!")
            return redirect('mover_dashboard')  # Redirect to mover dashboard
    else:
        form = MoverRegistrationForm()
    return render(request, 'users/register_mover.html', {'form': form})

# Dashboard Views
#@login_required
def dashboard(request):
    if hasattr(request.user, 'customer'):
        # Check if customer has filled out all profile information
        if not request.user.customer.phone or not request.user.customer.payment_info:
            messages.warning(request, "Please complete your profile information before placing an order.")
            return redirect('complete_profile')  # Redirect to profile completion page
        orders = Order.objects.filter(customer=request.user.customer)
        return render(request, 'users/dashboard.html', {'orders': orders})
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')

#@login_required
def mover_dashboard(request):
    if hasattr(request.user, 'mover'):
        orders = Order.objects.filter(items_detected__isnull=False).distinct()
        return render(request, 'users/mover_dashboard.html', {'orders': orders})
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')

# Order Creation & Image Processing
def create_order(request):
    if request.method == 'POST':
        order_form = OrderForm(request.POST)
        photo_formset = PhotoFormSet(request.POST, request.FILES, queryset=Photo.objects.none())

        if order_form.is_valid() and photo_formset.is_valid():
            order = order_form.save(commit=False)
            order.origin_location = request.POST.get('origin_location')
            order.destination_location = request.POST.get('destination_location')
            order.customer = request.user.customer  # Assign order to logged-in customer
            order.save()

            # YOLO Model for Image Processing
            yolo_model = YOLO('yolov8l.pt')  # Load YOLO model
            total_volume, total_weight = 0.0, 0.0

            for form in photo_formset.cleaned_data:
                if form:
                    photo_instance = Photo.objects.create(order=order, image=form['image'])
                    results = yolo_model(photo_instance.image.path)

                    # Process YOLO results
                    for result in results:
                        for box in result.boxes.data:
                            item_class_idx = int(box.cls.item())
                            item_class_name = yolo_model.names[item_class_idx]
                            estimates = VOLUME_WEIGHT_ESTIMATES.get(item_class_name, {"volume": 0, "weight": 0})

                            DetectedItem.objects.create(
                                order=order,
                                item_class=item_class_name,
                                confidence=float(box.conf.item()),
                                volume=estimates["volume"],
                                weight=estimates["weight"],
                                bbox={  # Store bounding box data
                                    'x1': float(box.xyxy[0].item()),
                                    'y1': float(box.xyxy[1].item()),
                                    'x2': float(box.xyxy[2].item()),
                                    'y2': float(box.xyxy[3].item())
                                }
                            )
                            total_volume += estimates["volume"]
                            total_weight += estimates["weight"]

            order.total_volume = total_volume
            order.total_weight = total_weight
            order.save()

            messages.success(request, "Order successfully created with detected items!")
            return redirect('dashboard')
    else:
        order_form = OrderForm()
        photo_formset = PhotoFormSet(queryset=Photo.objects.none())

    return render(request, 'users/create_order.html', {
        'order_form': order_form,
        'photo_formset': photo_formset
    })

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

    return redirect(session.url, code=303)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            order_id = session.get('metadata', {}).get('order_id')
            if order_id:
                order = Order.objects.get(id=order_id)
                order.paid = True
                order.save()
                return JsonResponse({"status": "success"}, status=200)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)
