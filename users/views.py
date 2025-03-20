import os
import logging
import json
import cv2
import numpy as np
import stripe
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from geopy.distance import geodesic
from django.core.files import File
from ultralytics import YOLO
from .models import (
    Order, Bid, Payment, SelectedMover, ProcessedImage, DetectedItem, Photo,
    Customer, Mover, CustomUser
)
from .forms import (
    MoverRegistrationForm, CustomerRegistrationForm, CustomUserLoginForm, 
    OrderForm, PhotoFormSet, MoverProfileForm, CustomerProfileForm, 
    UserProfileForm, PhotoUploadForm
)
from utils.volume_weight_estimates import VOLUME_WEIGHT_ESTIMATES


print("🔥 views.py is loaded!")  



logger = logging.getLogger(__name__)

# Load YOLO model
yolo_model = YOLO("yolov8x.pt")

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
            messages.error(request, "Please correct the errors below.")
    else:
        order_form = OrderForm()

    return render(request, 'users/create_order.html', {'order_form': order_form})

# Create Order Step 2
@login_required
def create_order_step2(request):
    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request, "No order found.")
        return redirect('create_order')

    order = get_object_or_404(Order, id=order_id)

    item_list = {item: data for item, data in VOLUME_WEIGHT_ESTIMATES.items()}
    vehicle_choices = [('Car', 'Car'), ('Small Van', 'Small Van'), ('Large Van', 'Large Van')]

    photos = Photo.objects.filter(order=order)
    detected_items = DetectedItem.objects.filter(order=order)

    context = {
        'photos': photos,
        'detected_items': detected_items,
        'item_list': item_list,
        'vehicle_choices': vehicle_choices,
        'volume_weight_estimates_json': json.dumps(VOLUME_WEIGHT_ESTIMATES)
    }

    if request.method == 'POST':
        if 'images' in request.FILES:
            image = request.FILES['images']
            photo = Photo(order=order, image=image)
            photo.save()

            detected_objects, processed_image_path = detect_objects(photo.image.path, order)

            with open(processed_image_path, 'rb') as img_file:
                photo.processed_image.save(os.path.basename(processed_image_path), File(img_file))
                photo.save()

            for obj in detected_objects:
                DetectedItem.objects.create(
                    order=order,
                    item_class=obj["item_class"],
                    confidence=obj["confidence"],
                    volume=obj["volume"],
                    weight=obj["weight"],
                    bbox=json.dumps(obj["bbox"])
                )

            messages.success(request, "Image processed successfully!")
            return redirect('create_order_step2')

        elif 'vehicle_type' in request.POST:
            vehicle_type = request.POST.get('vehicle_type')
            selected_items = request.POST.getlist('selected_items[]')

            order.vehicle_type = vehicle_type
            order.save()

            DetectedItem.objects.filter(order=order).delete()

            selected_items = selected_items if selected_items else []

            for item_json in selected_items:
                item = json.loads(item_json)
                DetectedItem.objects.create(
                    order=order,
                    item_class=item['item'],
                    volume=item['volume'],
                    weight=item['weight'],
                    confidence=100,
                    bbox=json.dumps({})
                )

            messages.success(request, "Order updated successfully!")
            return redirect('customer_dashboard')

    return render(request, 'users/create_order_step2.html', context)


def detect_objects(image_path, order):
    logger.info(f"Processing image for order {order.id}")

    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"Image not found: {image_path}")
        return [], image_path

    results = yolo_model.predict(image_path, conf=0.4)

    detected_items = []
    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()
        confidences = result.boxes.conf.cpu().numpy()
        classes = result.boxes.cls.cpu().numpy()

        for box, confidence, class_id in zip(boxes, confidences, classes):
            x1, y1, x2, y2 = map(int, box)
            item_name = yolo_model.names[int(class_id)]

            item_data = VOLUME_WEIGHT_ESTIMATES.get(item_name, {"volume": 0.5, "weight": 10.0})
            volume = item_data["volume"]
            weight = item_data["weight"]

            detected_items.append({
                "item_class": item_name,
                "confidence": float(confidence) * 100,
                "volume": volume,
                "weight": weight,
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            })

            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(image, f"{item_name} ({volume}m³, {weight}kg)", 
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                        (0, 255, 0), 2)

    processed_image_path = image_path.replace(".jpg", "_processed.jpg")
    cv2.imwrite(processed_image_path, image)

    with open(processed_image_path, 'rb') as img_file:
        processed_image = ProcessedImage(order=order) 
        processed_image.processed_image.save(os.path.basename(processed_image_path), File(img_file))
        processed_image.save()

    logger.info(f"Processed image saved: {processed_image_path}")

    return detected_items, processed_image_path



# Stripe Configuration
stripe.api_key = settings.STRIPE_SECRET_KEY

# User Authentication & Signup
def login_view(request):
    logger.info("Login attempt")

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        form = CustomUserLoginForm(request, data=request.POST)

        if form.is_valid():
            email = form.cleaned_data.get('username', "").strip().lower()  
            password = form.cleaned_data.get('password')

            if not email:
                messages.error(request, "Email field cannot be empty.")
                return render(request, 'registration/login.html', {'form': form, 'next': next_url})

            logger.debug(f"Authenticating user: {email}")

            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                request.session.save()
                logger.info(f"User {email} logged in successfully")

                return redirect('customer_dashboard' if hasattr(user, 'customer') else 'mover_dashboard')
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
    # Checkout and Process Payment

# Mark Mission as Done (Mover)
@login_required
def mark_order_as_done(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if not hasattr(request.user, 'mover'):
        messages.error(request, "Access denied. Only movers can mark an order as completed.")
        return redirect('home')

    if order.status != "Ongoing":
        messages.error(request, "This order cannot be marked as completed.")
        return redirect('mover_dashboard')

    order.status = "Awaiting Confirmation"
    order.save()

    messages.success(request, "Order marked as completed. Awaiting customer confirmation.")
    return redirect('mover_dashboard')

# Confirm Mission Complete (Customer)
@login_required
def confirm_mission_complete(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status != "Ongoing":
        return JsonResponse({"status": "error", "message": "Order is not in progress!"}, status=400)

    # Awaiting Confirmation"
    order.status = "Awaiting Confirmation"
    order.save()

    return JsonResponse({"status": "success", "message": "Order marked as awaiting confirmation!"})


# Customer Dashboard

logger = logging.getLogger(__name__) 

@login_required
def customer_dashboard(request):
    customer = request.user.customer

    orders = Order.objects.filter(customer=customer)
    received_bids = Bid.objects.filter(order__customer=customer, status="Pending").select_related('mover')
    selected_movers = SelectedMover.objects.filter(customer=customer).select_related('mover')
    payment_history = Payment.objects.filter(customer=customer).order_by('-date')

    total_price = sum(mover.price for mover in selected_movers) * Decimal(1.10)

    return render(request, 'users/customer_dashboard.html', {
        'orders': orders,
        'received_bids': received_bids,
        'selected_movers': selected_movers,
        'total_price': total_price,
        'payment_history': payment_history
    })

  

# Mover Dashboard
@login_required
def mover_dashboard(request):
    mover = request.user.mover

    orders = Order.objects.filter(status="Pending").distinct()
    sent_bids = Bid.objects.filter(mover=mover)
    accepted_orders = Order.objects.filter(bids__mover=mover, bids__status="Accepted").distinct()
    missions = SelectedMover.objects.filter(mover=mover, order__status="Ongoing")

    earnings = Payment.objects.filter(mover=mover)
    total_earnings = sum(payment.amount for payment in earnings) if earnings else 0

    return render(request, 'users/mover_dashboard.html', {
        'orders': orders,
        'sent_bids': sent_bids,
        'accepted_orders': accepted_orders,
        'missions': missions,
        'earnings': earnings,
        'total_earnings': total_earnings
    })



# Accept or Reject Orders
@login_required
def accept_order(request, order_id):
    logger.info("Accepting order: %s", order_id)
    order = get_object_or_404(Order, id=order_id)

    if not hasattr(request.user, 'mover'):
        messages.error(request, "Access denied.")
        return redirect('home')

    if order.status != 'Pending':
        messages.error(request, "This order is no longer available.")
        return redirect('mover_dashboard')

    order.status = 'Ongoing'
    order.save()

    bid, created = Bid.objects.get_or_create(order=order, mover=request.user.mover)
    bid.status = 'Accepted'
    bid.save()

    messages.success(request, "Order accepted successfully!")
    return redirect('mover_dashboard')


@login_required
def reject_order(request, order_id):
    logger.info("Rejecting order: %s", order_id)
    order = get_object_or_404(Order, id=order_id)

    if not hasattr(request.user, 'mover'):
        messages.error(request, "Access denied.")
        return redirect('home')

    bid = Bid.objects.filter(order=order, mover=request.user.mover).first()
    
    if bid:
        bid.status = 'Rejected'
        bid.save()
        messages.success(request, "Order rejected successfully!")
    else:
        messages.error(request, "You haven't placed a bid for this order.")

    return redirect('mover_dashboard')



# Order Details View
@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    processed_images = ProcessedImage.objects.filter(order=order)

    detected_items = DetectedItem.objects.filter(order=order)

    total_volume = sum(item.volume for item in detected_items)
    total_weight = sum(item.weight for item in detected_items)
    total_items = detected_items.count()

    return render(request, 'users/order_details.html', {
        'order': order,
        'processed_images': processed_images,
        'detected_items': detected_items, 
        'total_volume': total_volume,
        'total_weight': total_weight,
        'total_items': total_items,
        'origin_lat': order.origin_lat,
        'origin_lng': order.origin_lng,
        'destination_lat': order.destination_lat,
        'destination_lng': order.destination_lng
    })



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

@login_required
def process_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    amount = sum(m.price for m in SelectedMover.objects.filter(order=order))

    order.status = "Ongoing"
    order.save()

    Payment.objects.create(
        customer=order.customer,
        amount=amount,
        status="Completed"
    )

    return JsonResponse({
        "status": "success",
        "message": f"Payment of ${amount} completed successfully! Order is now in progress."
    })

    payment = Payment.objects.create(
        customer=order.customer,
        amount=amount,
        status="Pending",
    )
    payment.save()

    return redirect(session.url)


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


# Edit profile
@login_required
def edit_profile(request):
    logger.info("Editing profile for user: %s", request.user)

    user_form = UserProfileForm(request.POST or None, request.FILES or None, instance=request.user)

    if hasattr(request.user, 'customer'):
        user_type = 'customer'
        profile_form = CustomerProfileForm(request.POST or None, request.FILES or None, instance=request.user.customer)
        dashboard_redirect = 'customer_dashboard'

    elif hasattr(request.user, 'mover'):
        user_type = 'mover'
        profile_form = MoverProfileForm(request.POST or None, request.FILES or None, instance=request.user.mover)
        dashboard_redirect = 'mover_dashboard'

    else:
        messages.error(request, "Access denied.")
        return redirect('home')

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            
            new_password = user_form.cleaned_data.get('new_password')
            confirm_password = user_form.cleaned_data.get('confirm_password')

            if new_password and confirm_password and new_password == confirm_password:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, "Profile and password updated successfully! Please log in again.")
                logout(request)
                return redirect('login')

            messages.success(request, "Profile updated successfully!")
            return redirect(dashboard_redirect)

    return render(request, 'users/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_type': user_type
    })
#remove_detected_item
@login_required
def remove_detected_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(DetectedItem, id=item_id)

        if item.order.customer != request.user.customer:
            return JsonResponse({'error': 'Unauthorized action'}, status=403)

        item.delete()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)



@login_required
def mark_order_as_done(request, order_id):
   
    order = get_object_or_404(Order, id=order_id)

    if not hasattr(request.user, 'mover'):
        messages.error(request, "Access denied. Only movers can mark an order as completed.")
        return redirect('home')

    if order.status != "Ongoing":
        messages.error(request, "This order cannot be marked as completed.")
        return redirect('mover_dashboard')

    order.status = "Awaiting Confirmation"
    order.save()

    messages.success(request, "Order marked as completed. Awaiting customer confirmation.")
    return redirect('mover_dashboard')



# accept_order
@login_required
def accept_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'Pending': 
        order.status = 'Ongoing'
        order.save()
        messages.success(request, "Order accepted successfully!")
    else:
        messages.error(request, "This order is not available for acceptance.")
    return redirect('mover_dashboard')

# reject_order
@login_required
def reject_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'Pending':
        order.status = 'Rejected'
        order.save()
        messages.success(request, "Order rejected successfully!")
    else:
        messages.error(request, "This order cannot be rejected.")
    return redirect('mover_dashboard')

#place bid
@login_required
def place_bid(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        price = request.POST.get("bid_price")
        if price:
            Bid.objects.create(order=order, mover=request.user.mover, price=price, status="Pending")
            messages.success(request, "Your bid has been placed successfully!")
    return redirect("mover_dashboard")


# Accept Bid and Move to Checkout
@login_required
def accept_bid(request, bid_id):
    bid = get_object_or_404(Bid, id=bid_id)

    if request.user.customer != bid.order.customer:
        return JsonResponse({"status": "error", "message": "Unauthorized access"}, status=403)

    Bid.objects.filter(order=bid.order).delete()

    selected_mover = SelectedMover.objects.create(
        customer=request.user.customer,
        order=bid.order,
        mover=bid.mover,
        price=bid.price
    )

    return JsonResponse({
        "status": "success",
        "message": "Bid accepted! Moved to checkout.",
        "mover_name": selected_mover.mover.full_name,
        "order_name": f"{bid.order.origin} → {bid.order.destination}",
        "price": selected_mover.price
    })

# mover profile

def mover_profile(request, mover_id):
    mover = get_object_or_404(Mover, id=mover_id)
    return render(request, 'users/mover_profile.html', {'mover': mover})


#customer_profile
def customer_profile(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    return render(request, 'users/customer_profile.html', {'customer': customer})



@login_required
def finalize_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status != "Awaiting Confirmation":
        return JsonResponse({"status": "error", "message": "Order is not ready for finalization!"}, status=400)

    for mover in SelectedMover.objects.filter(order=order):
        Payment.objects.create(
            customer=order.customer,
            amount=mover.price * 0.8,  
            status="Completed"
        )

    order.status = "Completed"
    order.save()

    return JsonResponse({"status": "success", "message": "Order completed and payments processed!"})
