from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.forms import modelformset_factory
from .models import Customer, Mover, Order, Photo

# --- Customer Registration Form ---
class CustomerRegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=100, label='Full Name', required=True)
    phone = forms.CharField(max_length=15, required=False)
    email = forms.EmailField(label='Email', required=True)
    profile_photo = forms.ImageField(required=False)
    payment_info = forms.CharField(max_length=255, required=False, help_text="Enter your payment information")

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2', 'full_name', 'phone', 'profile_photo', 'payment_info']

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('full_name') or not cleaned_data.get('email'):
            raise forms.ValidationError('Please fill out all required fields.')
        return cleaned_data

# --- Mover Registration Form ---
class MoverRegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=100, label='Full Name', required=True)
    phone = forms.CharField(max_length=15, required=True)
    email = forms.EmailField(label='Email', required=True)
    profile_photo = forms.ImageField(required=False)
    identification_id = forms.CharField(max_length=100, label='Identification ID (Passport, Work/Study Permit, SIN)')
    has_vehicle = forms.ChoiceField(choices=[('Yes', 'Yes'), ('No', 'No')], label='Do you have a vehicle?', required=True)
    vehicle_type = forms.ChoiceField(choices=[('Car', 'Car'), ('Small Van', 'Small Van'), ('Large Van', 'Large Van')], required=False)
    mover_type = forms.ChoiceField(choices=[('Pro Mover', 'Professional Mover'), ('Mover', 'Simple Mover'), ('Box Packer', 'Box Packer'), ('Driver with Help', 'Driver with Help'), ('Driver without Help', 'Driver without Help')], required=True)
    payment_info = forms.CharField(max_length=255, help_text="Enter your bank account details", required=True)
    driving_license = forms.ImageField(required=False, label='Upload Driving License')
    carrying_capacity = forms.IntegerField(label='Carrying Capacity (kg)', required=False)
    has_mover_certification = forms.BooleanField(required=False, label='Do you have Canadian Professional Mover Certification?')
    mover_certification_document = forms.ImageField(required=False, label='Upload Certification Document')

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2', 'full_name', 'phone', 'profile_photo', 'identification_id', 'has_vehicle', 'vehicle_type', 'mover_type', 'payment_info', 'driving_license', 'carrying_capacity', 'has_mover_certification', 'mover_certification_document']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already taken. Please choose a different one.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        has_vehicle = cleaned_data.get('has_vehicle')
        vehicle_type = cleaned_data.get('vehicle_type')
        move_capacity = cleaned_data.get('carrying_capacity')
        driving_license = cleaned_data.get('driving_license')

        if has_vehicle == 'Yes':
            if not vehicle_type:
                self.add_error('vehicle_type', 'Vehicle type is required if you have a vehicle.')
            if not move_capacity:
                self.add_error('carrying_capacity', 'Move Capacity is required if you have a vehicle.')
            if not driving_license:
                self.add_error('driving_license', 'Driving License is required if you have a vehicle.')
        
        if cleaned_data.get('has_mover_certification') and not cleaned_data.get('mover_certification_document'):
            self.add_error('mover_certification_document', 'Certification Document is required if you have Canadian Mover Certification.')
        
        return cleaned_data

# --- Custom User Login Form ---
class CustomUserLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', required=True)
    password = forms.CharField(widget=forms.PasswordInput, label='Password', required=True)

# --- Order Form ---
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['origin', 'destination', 'origin_floor', 'destination_floor', 'has_elevator', 'need_pro_mover', 'need_box_packer', 'move_date', 'origin_location', 'destination_location']

# --- Photo FormSet ---
PhotoFormSet = modelformset_factory(Photo, fields=('image',), extra=1)