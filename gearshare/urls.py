from django.urls import path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from allauth.account.views import LogoutView as AllauthLogoutView

from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = "gearshare"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('sign-out', views.sign_out, name='sign_out'),
    path('auth-receiver', views.auth_receiver, name='auth_receiver'),
    path('profile/', views.profile, name='profile'),
    path('items/', views.items, name='items'),
    path('items/<slug:slug>-<int:id>/', views.item_detail, name='item_detail'),
    path('items/<int:item_id>/rate/', views.add_rating, name='add_rating'),
    path('items/<int:item_id>/ratings/', views.view_ratings, name='view_ratings'),
    path('items/<int:item_id>/edit/', views.edit_item, name='edit_item'),
    path('items/<int:item_id>/delete/', views.delete_item, name='delete_item'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('search/', views.item_search, name='search'),
    path('collections/', views.collections, name="collections"),
    path('collections/add/', views.add_collection, name="add_collection"),
    path('collections/<int:collection_id>/edit/', views.edit_collection, name='edit_collection'),
    path('collections/<int:collection_id>/', views.view_collection, name='view_collection'),
    path('librarian_dashboard/', views.librarian_dashboard, name='librarian_dashboard'),
    path('items/<int:item_id>/borrow/', views.borrow_item, name='borrow_item'),
    path('collections/<int:collection_id>/delete/', views.delete_collection, name="delete_collection"),
    path('ratings/<int:rating_id>/delete/', views.delete_rating, name='delete_rating'),
    path('borrow_request/<int:request_id>/accept/', views.accept_borrow_request, name='accept_borrow_request'),
    path('borrow_request/<int:request_id>/deny/', views.deny_borrow_request, name='deny_borrow_request'),
    path('collections/<int:collection_id>/request_access/', views.request_collection_access, name='request_collection_access'),
    path('collection_request/<int:request_id>/accept/', views.accept_collection_request, name='accept_collection_request'),
    path('collection_request/<int:request_id>/deny/', views.deny_collection_request, name='deny_collection_request'),
    path('user/<int:user_id>/promote/', views.promote_user, name='promote_user'),
    # path('user/<int:user_id>/demote/', views.demote_user, name='demote_user'),
    #for shopping cart
    path('checkout/', views.checkout_page, name='checkout_page'),
    #collection serarch
    path('collections/search/', views.collection_search, name='collection_search'),
    path('collections/<int:collection_id>/search/', views.collection_item_search, name='collection_item_search'),
    path('checkout/', views.checkout_page, name='checkout_page'),
    path('borrow_request/<int:request_id>/delete/', views.delete_borrow_request, name='delete_borrow_request'),
    path('clear_notifications/', views.clear_notifications, name='clear_notifications'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
