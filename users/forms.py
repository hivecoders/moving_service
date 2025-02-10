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
    vehicle_type = forms.ChoiceField(choices=[('Car', 'Car'), ('Small Van', 'Small Van'), ('Large Van', 'Large Van')], required=True)
    mover_type = forms.ChoiceField(choices=[
        ('Pro Mover', 'Professional Mover'),
        ('Mover', 'Simple Mover'),
        ('Box Packer', 'Box Packer'),
        ('Driver with Help', 'Driver with Help'),
        ('Driver without Help', 'Driver without Help')
    ], required=True)
    location = forms.CharField(max_length=255, required=True)
    payment_info = forms.CharField(max_length=255, help_text="Enter your bank account details", required=True)
    driving_license = forms.ImageField(required=False, label='Upload Driving License')
    carrying_capacity = forms.IntegerField(label='Carrying Capacity (kg)', required=False)
    has_mover_certification = forms.BooleanField(required=False, label='Do you have Canadian Professional Mover Certification?')
    mover_certification_document = forms.ImageField(required=False, label='Upload Certification Document')

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2', 'full_name', 'phone', 'profile_photo', 'identification_id',
                  'vehicle_type', 'mover_type', 'location', 'payment_info', 'driving_license', 'carrying_capacity',
                  'has_mover_certification', 'mover_certification_document']

    def clean(self):
        cleaned_data = super().clean()
        vehicle_type = cleaned_data.get('vehicle_type')
        move_capacity = cleaned_data.get('carrying_capacity')
        driving_license = cleaned_data.get('driving_license')

        if vehicle_type and not move_capacity:
            self.add_error('carrying_capacity', 'Move Capacity is required if you have a vehicle.')
        
        if vehicle_type and not driving_license:
            self.add_error('driving_license', 'Driving License is required if you have a vehicle.')
        
        if cleaned_data.get('has_mover_certification') and not cleaned_data.get('mover_certification_document'):
            self.add_error('mover_certification_document', 'Certification Document is required if you have Canadian Mover Certification.')
        
        return cleaned_data


# --- User Login Form ---
class CustomUserLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')

# --- Order Creation Form ---
class OrderForm(forms.ModelForm):
    origin_location = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Select Origin on Map', 'class': 'form-control'}))
    destination_location = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Select Destination on Map', 'class': 'form-control'}))

    class Meta:
        model = Order
        fields = ['origin', 'origin_location', 'origin_floor', 'destination', 'destination_location',
                  'destination_floor', 'has_elevator', 'need_pro_mover', 'need_box_packer', 'move_date']

# --- Single Photo Upload Form ---
class SinglePhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control mb-2'})
        }

# --- FormSet for Multiple Photo Uploads ---
PhotoFormSet = modelformset_factory(Photo, form=SinglePhotoForm, extra=3)
