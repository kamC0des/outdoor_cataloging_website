from django import forms
from .models import Item, Profile, Collection, Rating, BorrowRequest
from django.core.exceptions import ValidationError
from datetime import date, timedelta

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['title', 'status', 'category', 'condition', 'location', 'description', 'image']
class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture']

class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['title', 'description', 'items', 'is_public', 'allowed_users']
        widgets = {
            'items': forms.CheckboxSelectMultiple(),
            'allowed_users': forms.CheckboxSelectMultiple(),
        }
class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }

    user = forms.CharField(widget=forms.HiddenInput(), required=False)
    item = forms.CharField(widget=forms.HiddenInput(), required=False)
class BorrowRequestForm(forms.ModelForm):
    class Meta:
        model = BorrowRequest
        fields = ['requested_start_date', 'requested_end_date', 'message']
        widgets = {
            'requested_start_date': forms.DateInput(attrs={'type': 'date'}),
            'requested_end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('requested_start_date')
        end_date = cleaned_data.get('requested_end_date')
        
        if start_date and end_date:
            if start_date < date.today():
                raise ValidationError("Start date cannot be in the past")
            if end_date < start_date:
                raise ValidationError("End date must be after start date")
            if (end_date - start_date).days > 14:
                raise ValidationError("You cannot borrow items for more than 14 days")
        return cleaned_data
class ReturnItemForm(forms.Form):
    CONDITION_CHOICES = [
        ('available', 'Item is in good condition'),
        ('maintenance', 'Item needs repair'),
        ('lost', 'Item is lost or severely damaged'),
    ]
    
    condition = forms.ChoiceField(
        choices=CONDITION_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Please provide any additional details about the item's condition"
    )