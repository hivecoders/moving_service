import logging
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.timezone import now
import uuid

logger = logging.getLogger(__name__)

# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email).lower()
        logger.info(f"Creating user with email: {email}")
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

# Custom User Model
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

# Customer Model
class Customer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, default="0000000000")
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)

    def __str__(self):
        return f"Customer: {self.user.full_name} - {self.user.email}"

# Mover Model
class Mover(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    vehicle_type = models.CharField(
        max_length=100,
        choices=[("Car", "Car"), ("Small Van", "Small Van"), ("Large Van", "Large Van")],
        null=True,
        blank=True,
    )
    mover_type = models.CharField(
        max_length=20,
        choices=[
            ("Pro Mover", "Professional Mover"),
            ("Mover", "Simple Mover"),
            ("Box Packer", "Box Packer"),
            ("Driver with Help", "Driver with Help"),
            ("Driver without Help", "Driver without Help"),
        ],
    )
    location = models.CharField(max_length=255)
    payment_info = models.CharField(max_length=255)
    driving_license = models.ImageField(upload_to="licenses/", null=True, blank=True)
    carrying_capacity = models.IntegerField(null=True, blank=True)
    identification_id = models.CharField(max_length=100, null=True, blank=True)
    has_vehicle = models.BooleanField(default=False)
    has_mover_certification = models.BooleanField(default=False)
    mover_certification_document = models.ImageField(upload_to="certifications/", null=True, blank=True)

    def __str__(self):
        return f"Mover: {self.user.full_name} - {self.user.email}"



#Order

class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Ongoing", "Ongoing"),
        ("Completed", "Completed"),
        ("Canceled", "Canceled"),
    ]

    customer = models.ForeignKey("Customer", on_delete=models.CASCADE, related_name="customer_orders")
    order_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    origin_floor = models.IntegerField(null=True, blank=True)
    destination_floor = models.IntegerField(null=True, blank=True)
    has_elevator = models.BooleanField(default=False)
    need_pro_mover = models.BooleanField(default=False)
    need_box_packer = models.BooleanField(default=False)
    move_date = models.DateField()
    move_time = models.TimeField(null=True, blank=True)
    origin_location = models.CharField(max_length=100)
    destination_location = models.CharField(max_length=100)
    origin_lat = models.FloatField(null=True, blank=True)
    origin_lng = models.FloatField(null=True, blank=True)
    destination_lat = models.FloatField(null=True, blank=True)
    destination_lng = models.FloatField(null=True, blank=True)
    total_volume = models.FloatField(default=0)
    total_weight = models.FloatField(default=0)
    items_detected = models.ManyToManyField("DetectedItem", blank=True, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(default=now)
    bids = models.ManyToManyField('Bid', related_name="order_bids", blank=True)

    def __str__(self):
        return f"Order {self.order_code} by {self.customer.user.email}"


# Bid
class Bid(models.Model):
    order = models.ForeignKey(Order, related_name="bids_list", on_delete=models.CASCADE)
    mover = models.ForeignKey("Mover", on_delete=models.CASCADE, related_name="mover_bids")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, 
        choices=[("Pending", "Pending"), ("Accepted", "Accepted"), ("Rejected", "Rejected")], 
        default="Pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_winner = models.BooleanField(default=False)  # ✅ اضافه شد

    def __str__(self):
        return f"Bid by {self.mover} for Order #{self.order.id} - ${self.price}"

#SelectedMover
class SelectedMover(models.Model):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE, related_name="selected_movers")
    mover = models.ForeignKey("Mover", on_delete=models.CASCADE, related_name="selected_movers")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="selected_movers")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)  # باید این فیلد اضافه شده باشه
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Selected {self.mover} for Order #{self.order.id} - ${self.price}"

# Payment
class Payment(models.Model):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Failed", "Failed")], default="Completed")

    def __str__(self):
        return f"Payment of ${self.amount} by {self.customer} on {self.date}"

# Detected Items Model
class DetectedItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="detected_items")
    item_class = models.CharField(max_length=50)
    confidence = models.FloatField()
    volume = models.FloatField(default=0.0)
    weight = models.FloatField(default=0.0)
    bbox = models.JSONField()
    image = models.ImageField(upload_to="detected_items/", default="default.jpg")  # این خط اضافه شد ✅

    def __str__(self):
        return f"{self.item_class} (Confidence: {self.confidence * 100:.2f}%)"


# Photos Model
class Photo(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="photos/")
    processed_image = models.ImageField(upload_to="photos/processed/", null=True, blank=True)

    def __str__(self):
        return f"Photo for Order #{self.order.id}"
    
#ProcessedImage

class ProcessedImage(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="processed_images")
    processed_image = models.ImageField(upload_to='processed_images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Processed Image for Order #{self.order.id}"

class Review(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="review")
    mover = models.ForeignKey(Mover, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=[(1, "⭐"), (2, "⭐⭐"), (3, "⭐⭐⭐"), (4, "⭐⭐⭐⭐"), (5, "⭐⭐⭐⭐⭐")])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.mover.user.full_name} - {self.rating}⭐"
    

class MoverProfile(models.Model):
    mover = models.OneToOneField(Mover, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(null=True, blank=True)
    experience_years = models.IntegerField(default=0)
    certifications = models.TextField(null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Profile for {self.mover.user.full_name}"
