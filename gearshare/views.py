import os
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Profile, Item, Collection, BorrowRequest, CollectionRequest, Rating, Notifications
from .forms import ItemForm, ProfilePictureForm, CollectionForm, RatingForm, BorrowRequestForm, ReturnItemForm
from datetime import date
import logging
from botocore.exceptions import ClientError
from django.utils import timezone
from django.db.models import Count

logger = logging.getLogger(__name__)

@csrf_exempt
def home(request):
    # if not request.user.is_authenticated:
    #     return redirect('gearshare:login')
    return render(request, 'gearshare/home.html', {
                        'google_redirect_uri': settings.GOOGLE_OAUTH_REDIRECT
                    })


def profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    notifications = Notifications.objects.filter(user=profile).order_by('-timestamp')
    checked_out_items = Item.objects.filter(user=profile, status='checked_out')
    return render(request, 'gearshare/profile2.html', {
        'profile': profile,
        'is_librarian': profile.is_librarian,
        'join_date': profile.join_date,
        'notifications': notifications,
        'checked_out_items': checked_out_items,
    })

def sign_out(request):
    logout(request)
    return redirect('gearshare:home')

def collections(request):
    if not request.user.is_authenticated:
        collections = Collection.objects.filter(is_public=True).order_by('-last_updated')
        return render(request, "gearshare/collections.html", {
            'collections': collections,
            'is_anonymous': True
        })

    try:
        profile = Profile.objects.get(user=request.user)
        collections = Collection.objects.all().order_by('-last_updated')  # handle private collection logic in template
        # if not profile.is_librarian:
        #     collections = (collections | Collection.objects.filter(allowed_users=profile)).distinct()
        return render(request, "gearshare/collections.html", {
            'profile': profile,
            'collections': collections,
            'is_anonymous': False
        })
    except Profile.DoesNotExist:
        collections = Collection.objects.filter(is_public=True)
        return render(request, "gearshare/collections.html", {
            'collections': collections,
            'is_anonymous': False
        })

#changed so that partron can't even create a private collection
def add_collection(request):
    if not request.user.is_authenticated:
        return redirect('gearshare:home')

    profile = get_object_or_404(Profile, user=request.user)
    
    if request.method == "POST":
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.creator = profile
            if not profile.is_librarian:
                collection.is_public = True  
            collection.save()
            form.save_m2m()
            return redirect('gearshare:collections')
    else:
        form = CollectionForm()
    
    return render(request, 'gearshare/add_collections.html', {
        'form': form,
        'is_librarian': profile.is_librarian  # Pass to template
    })

#changed so that anonymous user can see items
def items(request):
    if request.user.is_authenticated:
        profile = Profile.objects.get(user=request.user)
    else:
        profile = None
    
    # Get items that are either not in any collection or in public collections
    items = None
    if profile and profile.is_librarian:
        items = Item.objects.all()
    else:
        # only display public items
        private_items = set()
        private_collections = Collection.objects.filter(is_public=False)

        for private_collection in private_collections:
            for item in private_collection.items.all():
                private_items.add(item)
        
        private_items_queryset = Item.objects.filter(id__in=[item.id for item in private_items])

        items = Item.objects.all().exclude(id__in=private_items_queryset.values_list('id', flat=True))

    

    if request.method == 'POST' and request.user.is_authenticated and profile.is_librarian:
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.save()  # This creates the ID
            
            # Now add collections if needed
            if 'collections' in form.cleaned_data:
                for collection in form.cleaned_data['collections']:
                    item.collections.add(collection)
            
            return redirect('gearshare:items')
    else:
        form = ItemForm() if (request.user.is_authenticated and profile.is_librarian) else None

    return render(request, 'gearshare/items.html', {
        'items': items, 
        'form': form, 
        'profile': profile,
        'is_anonymous': not request.user.is_authenticated
    })
@login_required
def edit_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    if not request.user.profile.is_librarian:
        return HttpResponseForbidden("Only librarians can edit items")
    
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('gearshare:item_detail', slug=item.slug, id=item.id)
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'gearshare/edit_item.html', {'form': form, 'item': item})

@login_required
def delete_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    if not request.user.profile.is_librarian:
        return HttpResponseForbidden("Only librarians can delete items")
    
    if request.method == "POST":
        item.delete()
        return redirect('gearshare:items')
    
    return redirect('gearshare:item_detail', slug=item.slug, id=item.id)

def item_detail(request, slug, id):
    item = get_object_or_404(Item, id=id)
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER')
    return render(request, 'gearshare/item_detail.html', {
        'item': item,
        'next': next_url
    })

@login_required
def upload_profile_picture(request):
    profile = Profile.objects.get(user=request.user)
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            uploaded_file = request.FILES.get('profile_picture')
            if uploaded_file:
                try:
                    profile.profile_picture.save(uploaded_file.name, uploaded_file, save=True)
                    logger.info(f"Successfully uploaded {uploaded_file.name} to S3")
                    return redirect('gearshare:profile')
                except Exception as e:
                    logger.error(f"Upload failed: {e}")
                    return HttpResponse(f"Upload failed: {e}", status=500)
            else:
                logger.warning("No file detected in request.FILES")
                return HttpResponse("No file detected", status=400)
        else:
            logger.error(f"Form errors: {form.errors}")
            return HttpResponse("Invalid form data", status=400)
    else:
        form = ProfilePictureForm(instance=profile)
    return render(request, 'gearshare/upload_profile_picture.html', {'form': form})


"""
*  REFERENCES
*  Title: The simplest way to add Google sign-in to your Django app ✍️
*  Author: Tom Dekan
*  Date: Jan 11, 2024
*  URL: https://tomdekan.com/articles/google-sign-in
"""
@csrf_exempt
def auth_receiver(request):
    """
    Google calls this URL after the user has signed in with their Google account.
    """
    print("Google auth_receiver was triggered!")
    token = request.POST.get('credential')
    print("Received token:", token)    
    try:
        user_data = id_token.verify_oauth2_token(
            token, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError:
        return HttpResponse("Invalid Google token", status=403)

    email = user_data.get('email')
    real_name = user_data.get('name', '')
    # profile_picture = user_data.get('picture', '')

    # check if the user already exists, if not, store the jaunt
    user, created = User.objects.get_or_create(
        username=email, 
        defaults={'email': email}  # set default username to email
    )
    
    if created:  # a new user was created
        Profile.objects.create(
            user=user,
            real_name=real_name,
            email=email,
            # check if user is a stored librarian
            is_librarian=email in getattr(settings, "LIBRARIAN_EMAILS", set())  
        )

    # set user authentication to google auth
    user.backend = 'allauth.account.auth_backends.AuthenticationBackend'

    # log user in
    login(request, user, backend=user.backend)
    

    # store user data in session
    request.session['user_data'] = {
        'email': email,
        'real_name': real_name,
        # 'profile_picture': profile_picture,
        'is_librarian': user.profile.is_librarian
    }

    print(request.session.get("user_data", {}))

    return redirect('gearshare:home')

def item_search(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    location = request.GET.get('location', '')

    results = Item.objects.all()

    if not request.user.is_authenticated or not request.user.profile.is_librarian:
        private_items = set()
        private_collections = Collection.objects.filter(is_public=False)

        for private_collection in private_collections:
            for item in private_collection.items.all():
                private_items.add(item)
        
        private_items_queryset = Item.objects.filter(id__in=[item.id for item in private_items])
        results = results.exclude(id__in=private_items_queryset.values_list('id', flat=True))

    if query:
        results = results.filter(title__icontains=query)
    if category:
        results = results.filter(category__icontains=category)
    if location:
        results = results.filter(location__icontains=location)

    context = {
        'results': results,
        'query': query,
        'category': category,
        'location': location,
    }
    return render(request, 'gearshare/item_search_results.html', context)


@login_required
def add_rating(request, item_id):
    profile = get_object_or_404(Profile, user=request.user)
    item = get_object_or_404(Item, pk=item_id)
    existing_rating = Rating.objects.filter(item=item, user=profile).first()
    if request.method == "POST":
        if existing_rating:
            # If rating exists, update it instead of creating new one
            form = RatingForm(request.POST, instance=existing_rating)
        else:
            form = RatingForm(request.POST)
            
        if form.is_valid():
            try:
                rating = form.save(commit=False)
                if not existing_rating:
                    rating.item = item
                    rating.user = profile
                rating.save()
                return redirect('gearshare:item_detail', slug=item.slug, id=item.id)
            except Exception as e:
                logger.error(f"Error saving rating: {e}")
                return HttpResponse("Error saving rating", status=500)
    else:
        if existing_rating:
            # Pre-populate form with existing rating
            form = RatingForm(instance=existing_rating)
        else:
            form = RatingForm()


    return render(request, 'gearshare/add_rating.html', {
        'form': form,
        'profile': profile,
        'item': item  # Pass the whole item object to template
    })
#view rating page
def view_ratings(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    ratings = item.ratings.all().select_related('user')
    
    # Prefetch profiles to avoid N+1 queries
    user_ids = [rating.user_id for rating in ratings]
    profiles = Profile.objects.filter(user_id__in=user_ids)
    profile_dict = {profile.user_id: profile for profile in profiles}
    
    for rating in ratings:
        rating.user.profile = profile_dict.get(rating.user_id)
    
    return render(request, 'gearshare/view_ratings.html', {
        'item': item,
        'ratings': ratings,
        'profile': request.user.profile if request.user.is_authenticated else None
    })
@login_required
def delete_rating(request, rating_id):
    rating = get_object_or_404(Rating, pk=rating_id)
    
    # Only allow the rating owner to delete
    if rating.user.user != request.user:
        return HttpResponseForbidden("You can only delete your own ratings")
    
    item = rating.item
    rating.delete()
    return redirect('gearshare:item_detail', slug=item.slug, id=item.id)
    

def view_collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)

    # Check if user has access to view this collection
    if not collection.is_public and not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)
    
    if request.user.is_authenticated:
        profile = get_object_or_404(Profile, user=request.user)
        if not collection.is_public and profile not in collection.allowed_users.all() and not profile.is_librarian:
            return HttpResponse("Unauthorized", status=401)
    
    items = collection.items.all()
    
    return render(request, 'gearshare/view_collection.html', {
        'collection': collection,
        'items': items,
        'is_librarian': request.user.profile.is_librarian if request.user.is_authenticated else False
    })

@login_required
def edit_collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    profile = get_object_or_404(Profile, user=request.user)
    
    # Only collection creator or librarians can edit
    if not profile.is_librarian and collection.creator != profile:
        return HttpResponse("Unauthorized", status=403)

    # Get all items not already in this collection
    available_items = Item.objects.exclude(id__in=collection.items.values_list('id', flat=True))
    if collection.is_public:
        print("this jaunt public")
        # Exclude items that are in any private collection
        private_items = set()
        private_collections = Collection.objects.filter(is_public=False)

        for private_collection in private_collections:
            for item in private_collection.items.all():
                private_items.add(item)
        
        private_items_queryset = Item.objects.filter(id__in=[item.id for item in private_items])
        available_items = available_items.exclude(id__in=private_items_queryset.values_list('id', flat=True))
    else:
        print("this jaunt private")
        # Keep only items that are in no collections at all
        available_items = available_items.filter(collection__isnull=True)


    form = CollectionForm(request.POST, instance=collection)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "edit_details":
            form = CollectionForm(request.POST, instance=collection)
            form.fields.pop('items', None)  # DONT CHANGE ITEM LIST !
            form.fields.pop('is_public', None)
            if form.is_valid():
                collection = form.save(commit=False)
                if not profile.is_librarian:
                    collection.is_public = True
                collection.save()
                form.save_m2m()
                return redirect('gearshare:view_collection', collection_id=collection.id)
            
        elif form_type == "add_items":
            item_ids = request.POST.getlist("add_items")
            add_items = Item.objects.filter(id__in=item_ids)
            collection.items.add(*add_items)
            return redirect('gearshare:edit_collection', collection_id=collection.id)
        
        elif form_type == "remove_item":
            item_id = request.POST.get("remove_item_id")
            if item_id:
                item = get_object_or_404(Item, id=item_id)
                collection.items.remove(item)
            return redirect('gearshare:edit_collection', collection_id=collection.id)
    else:
        form = CollectionForm(instance=collection)

        # only want to have the option of granting access to non-librarians (also, don't include ourselves)
        non_librarians = Profile.objects.filter(is_librarian=False).exclude(id=collection.creator.id)
        form.fields['allowed_users'].queryset = non_librarians
    
    return render(request, 'gearshare/edit_collection.html', {
        'collection': collection,
        'form': form,
        'available_items': available_items,
        'current_items': collection.items.all(),
        'is_librarian': profile.is_librarian
    })

@login_required
def delete_collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    profile = request.user.profile

    if collection.creator != profile:
        return HttpResponse("Unauthorized", status=403)
    
    if request.method == "POST":
        collection.delete()
        return redirect('gearshare:collections')
    
    return redirect('gearshare:collections')

def librarian_dashboard(request):
    profile = Profile.objects.get(user=request.user)
    if not profile.is_librarian:
        return render(request, 'not_authorized.html')
    
    borrow_requests = BorrowRequest.objects.all().order_by('-request_date')
    collection_requests = CollectionRequest.objects.all().order_by('-request_date')
    users = Profile.objects.all().order_by('real_name')
    return render(request, 'gearshare/librarian_dashboard.html', {
        'borrow_requests': borrow_requests,
        'collection_requests': collection_requests,
        'users': users
    })
# grady's code 
# @login_required
# def borrow_item(request, item_id):
#     if request.method == "POST":
#         item = get_object_or_404(Item, id=item_id)
#         profile = request.user.profile
#         message = request.POST.get("message", "")
#         BorrowRequest.objects.create(user=profile, item=item, message=message)
#         return redirect("gearshare:item_detail", slug=item.slug, id=item.id)

#eddie's borrow item
def borrow_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    if request.method == "POST":
        form = BorrowRequestForm(request.POST)
        if form.is_valid():
            if not request.POST.get('agreement_accepted') or request.POST.get('agreement_accepted') != "true":
                messages.error(request, "You must accept the borrower agreement")
                return redirect("gearshare:borrow_item", item_id=item.id)
            
            can_borrow, reason = item.can_be_borrowed(request.user)
            if can_borrow:
                borrow_request = form.save(commit=False)
                borrow_request.user = request.user.profile
                borrow_request.item = item
                borrow_request.agreement_accepted = True
                borrow_request.agreement_date = timezone.now()
                borrow_request.save()

                messages.success(request, f"Borrow request for {item.title} submitted successfully!")
                return redirect("gearshare:item_detail", slug=item.slug, id=item.id)
            else:
                messages.error(request, f"Cannot borrow item: {reason}")
        else:
            # Loop through form errors and show each as a toast
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)

    else:
        form = BorrowRequestForm()

    return render(request, 'gearshare/borrow_item.html', {
        'form': form,
        'item': item
    })

# views.py
def accept_borrow_request(request, request_id):
    if request.method == "POST":
        borrow_request = get_object_or_404(BorrowRequest, id=request_id)
        item = borrow_request.item

        # Update item status
        item.status = "checked_out"
        item.user = borrow_request.user
        item.due_date = borrow_request.requested_end_date  
        item.overdue_processed = False
        item.save()

        # Create notification for user
        Notifications.objects.create(
            user=borrow_request.user,
            message=f"Your borrow request for '{item.title}' has been accepted! The item is now checked out to you."
        )

        # Delete all borrow requests for this item
        BorrowRequest.objects.filter(item=item).delete()

        messages.success(request, f"Item {item.title} has been checked out to {borrow_request.user}")
        return redirect("gearshare:librarian_dashboard")

def deny_borrow_request(request, request_id):
    if request.method == "POST":
        try:
            borrow_request = BorrowRequest.objects.get(id=request_id)
            # Create notification for user
            Notifications.objects.create(
                user=borrow_request.user,
                message=f"Your borrow request for '{borrow_request.item.title}' has been denied."
            )
            borrow_request.delete()
            messages.success(request, "Borrow request has been denied.")
        except BorrowRequest.DoesNotExist:
            messages.error(request, "The borrow request could not be found. It may have already been processed.")
        
        return redirect("gearshare:librarian_dashboard")

@login_required
def request_collection_access(request, collection_id):
    if request.method == "POST":
        collection = get_object_or_404(Collection, id=collection_id)

        ####### CHECK (this should be unneccessary starting fresh)
        existing_request = CollectionRequest.objects.filter(
            user=request.user.profile, collection=collection
        ).first()

        if existing_request and not request.user.profile in collection.requested_users.all():
            print("add you to the jaunt")
            collection.requested_users.add(request.user.profile)
        #######################

        # ensure user has already requested access to the collection
        if not request.user.profile in collection.requested_users.all():
            CollectionRequest.objects.create(
                    user=request.user.profile,
                    collection=collection
                )
            print("created the jaunt")
            # keep track that this user has requested access
            collection.requested_users.add(request.user.profile)
        else:
            print("ooga booga")

        return redirect("gearshare:collections")

def accept_collection_request(request, request_id):
    if request.method == "POST":
        collection_request = get_object_or_404(CollectionRequest, id=request_id)
        collection = collection_request.collection
        user = collection_request.user
        
        # add user to collection
        collection.allowed_users.add(user)
        # remove user from list of users requesting access to collection
        collection.requested_users.remove(user)
        collection.save()

        # Create notification
        Notifications.objects.create(
            user=user,
            message=f"Your request to join the collection '{collection.title}' has been accepted!"
        )

        # delete request
        collection_request.delete()

    return redirect("gearshare:librarian_dashboard")

def deny_collection_request(request, request_id):
    if request.method == "POST":
        collection_request = get_object_or_404(CollectionRequest, id=request_id)
        collection = collection_request.collection
        user = collection_request.user

        # Create notification
        Notifications.objects.create(
            user=user,
            message=f"Your request to join the collection '{collection.title}' has been denied."
        )

        # delete the request
        collection_request.delete()
        collection.requested_users.remove(user)
        collection.save()

    return redirect("gearshare:librarian_dashboard")

def promote_user(request, user_id):
    if request.method == "POST":
        user = get_object_or_404(Profile, id=user_id)
        user.is_librarian = True
        user.save()

    return redirect("gearshare:librarian_dashboard")

# def demote_user(request, user_id):
#     if request.method == "POST":
#         user = get_object_or_404(Profile, id=user_id)
#         user.is_librarian = False
#         user.save()
    
#     return redirect("gearshare:librarian_dashboard")

#newly added shopping cart
# views.py
@login_required
def checkout_page(request):
    profile = request.user.profile
    notifications = Notifications.objects.filter(user=profile).order_by('-timestamp')
    if request.method == 'POST':
        form = ReturnItemForm(request.POST)
        if form.is_valid():
            item_id = request.POST.get('item_id')
            item = get_object_or_404(Item, id=item_id, user=profile)
            
            # Update item status and increment usage count
            item.status = form.cleaned_data['condition']
            item.user = None
            item.due_date = None  # Clear due date
            item.usage_count += 1
            item.save()
            
            messages.success(request, f"Item {item.title} has been returned")
            return redirect('gearshare:checkout_page')

    # Get currently borrowed items using the Item model's due_date
    pending_requests = BorrowRequest.objects.filter(user=profile, is_approved=False)
    borrowed_items = Item.objects.filter(user=profile, status='checked_out')
    
    return render(request, 'gearshare/checkout_page.html', {
        'pending_requests': pending_requests,
        'borrowed_items': borrowed_items,
        'notifications': notifications,
    })
def collection_search(request):
    query = request.GET.get('q', '')
    results = Collection.objects.filter(title__icontains=query)
    
    return render(request, 'gearshare/collection_search_results.html', {
        'results': results,
        'query': query
    })

def collection_item_search(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    query = request.GET.get('q', '')
    results = collection.items.filter(title__icontains=query)
    
    return render(request, 'gearshare/collection_item_search_results.html', {
        'collection': collection,
        'results': results,
        'query': query
    })

@login_required
def delete_borrow_request(request, request_id):
    if request.method == 'POST':
        borrow_request = get_object_or_404(BorrowRequest, id=request_id, user=request.user.profile)
        borrow_request.delete()
        messages.success(request, "Borrow request has been cancelled.")
    return redirect('gearshare:checkout_page')
@login_required
def clear_notifications(request):
    profile = Profile.objects.get(user=request.user)
    Notifications.objects.filter(user=profile).delete()
    return redirect('gearshare:checkout_page')