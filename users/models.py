import logging
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.timezone import now

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

# Order Model
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_orders")
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
    status = models.CharField(max_length=20, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"Order #{self.id} by {self.customer.user.email}"

# Detected Items Model
class DetectedItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="detected_items")
    item_class = models.CharField(max_length=50)
    confidence = models.FloatField()
    volume = models.FloatField(default=0.0)
    weight = models.FloatField(default=0.0)
    bbox = models.JSONField()

    def __str__(self):
        return f"{self.item_class} (Confidence: {self.confidence * 100:.2f}%)"

# Photos Model
class Photo(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="photos/")

    def __str__(self):
        return f"Photo for Order #{self.order.id}"
