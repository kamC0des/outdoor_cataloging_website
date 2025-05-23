from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import User
import uuid

from django.utils.text import slugify
import barcode
from barcode.writer import ImageWriter
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from io import BytesIO

from django.utils import timezone
from datetime import timedelta
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    real_name = models.CharField(max_length=255, default='')  
    email = models.EmailField(max_length=255, default='')  
    profile_picture = models.ImageField(
    upload_to='profiles/',
    default='profiles/default.jpg',
    blank=True
    )
    join_date = models.DateTimeField(auto_now_add=True)  
    is_librarian = models.BooleanField(default=False) 
    credit_score = models.PositiveSmallIntegerField(default=100)
    
    def check_overdue_items(self):
        overdue_items = Item.objects.filter(
            user=self,
            status='checked_out',
            due_date__lt=timezone.now().date(),
            overdue_processed=False
        )
        
        if overdue_items.exists():
            # Deduct points (10 per overdue item)
            deduction = 10 * overdue_items.count()
            self.credit_score = max(0, self.credit_score - deduction)
            self.save()
            
            # Mark items as processed
            overdue_items.update(overdue_processed=True)
            
            return True  # Indicates points were deducted
        return False

    def __str__(self):
        return self.real_name or self.email

class Item(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),       
        ('checked_out', 'Checked Out'),  
        ('reserved', 'Reserved'),        
        ('maintenance', 'Under Maintenance'), 
        ('lost', 'Lost/Damaged'),        
    ]
    
    CONDITION_CHOICES = [
        ('new', 'New'),       
        ('good', 'Good'),          
        ('fair', 'Fair'),          
        ('poor', 'Needs Repair'),  
        ('unusable', 'Unusable'),  
    ]
    
    CATEGORY_CHOICES = [
        ('camping', 'Camping'),
        ('climbing', 'Climbing'),
        ('water', 'Water Sports'),
        ('hiking', 'Hiking'),
        ('other', 'Other'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    title = models.CharField(max_length=200)
    barcode = models.ImageField(upload_to='barcodes/', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    location = models.CharField(max_length=100)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='items/', default='items/default.jpg')
    collections = models.ManyToManyField('Collection', blank=True)
    user = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='borrowed_items')
    last_updated = models.DateTimeField(auto_now=True)
    usage_count = models.PositiveIntegerField(default=0)
    due_date = models.DateField(null=True, blank=True)
    overdue_processed = models.BooleanField(default=False)
    slug = models.SlugField(blank=True)

    def save(self, *args, **kwargs):
        base_slug = slugify(self.title)
        creating = self.pk is None
        
        if not self.pk:  # Object not saved yet
            temp_slug = base_slug
        else:
            temp_slug = f"{base_slug}-{self.pk}"

        self.slug = temp_slug
        super().save(*args, **kwargs)

        if creating and not self.barcode:
            self.generate_barcode()
            self.slug = f"{base_slug}-{self.pk}"  # Add id to slug after ID exists
            super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        # Skip collection validation if the item hasn't been saved yet
        if self.pk is None:
            return
        
        # Get all private collections this item belongs to
        private_collections = self.collections.filter(is_public=False)
    
        if private_collections.exists():
            # If item is in any private collection, it can't be in any other collections
            if self.collections.count() > 1:
                raise ValidationError("An item in a private collection cannot be in any other collections")

    def generate_barcode(self):
        if self.id is None:
            return
        code_value = f"GEAR{self.id:04d}"  # Creates GEAR0001, GEAR0002, etc.
        code = barcode.get_barcode_class('code128')
        barcode_instance = code(code_value, writer=ImageWriter())
        buffer = BytesIO()
        barcode_instance.write(buffer)
        filename = f"barcode_{code_value}.png"
        self.barcode.save(filename, ContentFile(buffer.getvalue()), save=False)

    def can_be_borrowed(self, user):
        profile = user.profile
    
    # Check credit score
        if profile.credit_score < 60:
            return False, "Your credit score is too low (minimum 60 required)"
    
    # Check for overdue items
        overdue_items = Item.objects.filter(
            user=profile,
            status='checked_out',
            due_date__lt=timezone.now().date()
        )
        if overdue_items.exists():
            return False, "You have overdue items that need to be returned before borrowing new items"
    
    # Check if this specific item is already borrowed by someone
        if self.status == 'checked_out':
            return False, "This item is currently checked out by someone else"
    
        return True, ""
    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        if self.image and self.image.name != 'items/default.jpg':
            self.image.delete(save=False)  # Delete image from storage
        super().delete(*args, **kwargs)

class Rating(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )  # 1-5 stars
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('item', 'user') 

    def __str__(self):
        return f'{self.user} - {self.item.title} ({self.rating}/5)'

class Collection(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    items = models.ManyToManyField(Item, blank=True)
    is_public = models.BooleanField(default=True)
    allowed_users = models.ManyToManyField(Profile, blank=True, help_text='Users allowed to view and borrow from this private collection.')
    requested_users = models.ManyToManyField(Profile, related_name='requested_collections', blank=True)
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='collections', null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

def default_end_date():
    return timezone.now().date() + timedelta(days=7)

class BorrowRequest(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    requested_start_date = models.DateField(default=timezone.now)
    requested_end_date = models.DateField(default=default_end_date)  # use named function instead of lambda
    message = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    agreement_accepted = models.BooleanField(default=False)
    agreement_date = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f'{self.user} - {self.item.title}'
    
    class Meta:
        ordering = ['-request_date']

class CollectionRequest(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.collection.title}'
    
    class Meta: 
        unique_together = ('user', 'collection')  
        ordering = ['-request_date']

class Notifications(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.real_name}: {self.message[:20]}"
