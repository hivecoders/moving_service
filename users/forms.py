from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import modelformset_factory
from .models import Customer, Mover, Order, Photo, CustomUser

# Customer Registration Form
class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email',
        'required': 'required',
    }))
    full_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your full name',
        'required': 'required',
    }))
    phone = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your phone number',
        'required': 'required',
    }))
    profile_photo = forms.ImageField(widget=forms.FileInput(attrs={
        'class': 'form-control',
    }), required=False)

    class Meta:
        model = CustomUser
        fields = ['email', 'full_name', 'phone', 'profile_photo', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already taken. Please choose a different one.")
        return email

# Mover Registration Form
class MoverRegistrationForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your full name',
        'required': 'required',
    }))
    phone = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your phone number',
        'required': 'required',
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email',
        'required': 'required',
    }))
    profile_photo = forms.ImageField(widget=forms.FileInput(attrs={
        'class': 'form-control',
    }), required=False)
    identification_id = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Passport, Work/Study Permit, SIN',
        'required': 'required',
    }))
    has_vehicle = forms.ChoiceField(choices=[('Yes', 'Yes'), ('No', 'No')], widget=forms.Select(attrs={
        'class': 'form-control',
    }))
    vehicle_type = forms.ChoiceField(choices=[('Car', 'Car'), ('Small Van', 'Small Van'), ('Large Van', 'Large Van')], required=False, widget=forms.Select(attrs={
        'class': 'form-control',
    }))
    mover_type = forms.ChoiceField(choices=[
        ('Pro Mover', 'Professional Mover'),
        ('Mover', 'Simple Mover'),
        ('Box Packer', 'Box Packer'),
        ('Driver with Help', 'Driver with Help'),
        ('Driver without Help', 'Driver without Help')
    ], widget=forms.Select(attrs={
        'class': 'form-control',
    }))
    payment_info = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your bank account details',
        'required': 'required',
    }))
    driving_license = forms.ImageField(widget=forms.FileInput(attrs={
        'class': 'form-control',
    }), required=False)
    carrying_capacity = forms.IntegerField(widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': 'Carrying Capacity (kg)',
    }), required=False)
    has_mover_certification = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input',
        'id': 'certification_toggle'
    }))
    mover_certification_document = forms.ImageField(widget=forms.FileInput(attrs={
        'class': 'form-control',
        'id': 'certification_document'
    }), required=False)

    class Meta:
        model = CustomUser
        fields = ['email', 'password1', 'password2', 'full_name', 'phone', 'profile_photo', 'identification_id', 'has_vehicle', 'vehicle_type', 'mover_type', 'payment_info', 'driving_license', 'carrying_capacity', 'has_mover_certification', 'mover_certification_document']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if CustomUser.objects.filter(email=email).exists():
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

        mover_type = cleaned_data.get('mover_type')

        if mover_type == 'Pro Mover' and not cleaned_data.get('mover_certification_document'):
            self.add_error('mover_certification_document', 'Certification document is required for Pro Movers.')

        return cleaned_data

# Custom User Login Form
class CustomUserLoginForm(AuthenticationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email',
        'required': 'required',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your password',
        'required': 'required',
    }))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email").lower()
        password = cleaned_data.get("password")

        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Invalid email or password.")

        return cleaned_data

# Order Form
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['origin', 'destination', 'origin_floor', 'destination_floor', 'has_elevator', 'need_pro_mover', 'need_box_packer', 'move_date', 'origin_location', 'destination_location', 'total_volume', 'total_weight']

# Photo FormSet
PhotoFormSet = modelformset_factory(Photo, fields=('image',), extra=1)

# Mover Profile Form
class MoverProfileForm(forms.ModelForm):
    class Meta:
        model = Mover
        fields = ['full_name', 'phone', 'identification_id', 'has_vehicle', 'vehicle_type', 'mover_type', 'payment_info', 'driving_license', 'carrying_capacity', 'has_mover_certification', 'mover_certification_document']

# Customer Profile Form
class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['full_name', 'phone', 'profile_photo']

# Photo Upload Form
class PhotoUploadForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['image']
