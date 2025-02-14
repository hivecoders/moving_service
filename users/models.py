from django.db import models
from django.contrib.auth.models import User

# --- Customer Model ---
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, default="0000000000")
    email = models.EmailField(unique=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)  # Profile Photo

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

# --- Mover Model ---
class Mover(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    vehicle_type = models.CharField(max_length=100, choices=[('Car', 'Car'), ('Small Van', 'Small Van'), ('Large Van', 'Large Van')], null=True, blank=True)
    mover_type = models.CharField(max_length=20, choices=[('Pro Mover', 'Professional Mover'), ('Mover', 'Simple Mover'), ('Box Packer', 'Box Packer'), ('Driver with Help', 'Driver with Help'), ('Driver without Help', 'Driver without Help')])
    location = models.CharField(max_length=255)
    payment_info = models.CharField(max_length=255)
    driving_license = models.ImageField(upload_to='licenses/', null=True, blank=True)
    carrying_capacity = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.full_name

# --- Order Model ---
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    origin_floor = models.IntegerField(null=True, blank=True)
    destination_floor = models.IntegerField(null=True, blank=True)
    has_elevator = models.BooleanField(default=False)
    need_pro_mover = models.BooleanField(default=False)
    need_box_packer = models.BooleanField(default=False)
    move_date = models.DateTimeField()
    origin_location = models.CharField(max_length=100)
    destination_location = models.CharField(max_length=100)
    total_volume = models.FloatField(default=0)
    total_weight = models.FloatField(default=0)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.full_name}"

# --- DetectedItem Model for YOLO Detection ---
class DetectedItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items_detected')
    item_class = models.CharField(max_length=50)
    confidence = models.FloatField()
    volume = models.FloatField(default=0.0)  # Estimated volume in cubic meters
    weight = models.FloatField(default=0.0)  # Estimated weight in kilograms
    bbox = models.JSONField()

    def __str__(self):
        return f"{self.item_class} (Confidence: {self.confidence * 100:.2f}%)"

# --- Photo Model for Uploaded Images ---
class Photo(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='photos')
    image = models.FileField(upload_to='photos/')

    def __str__(self):
        return f"Photo for Order #{self.order.id}"
