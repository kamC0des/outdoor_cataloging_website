from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from gearshare.models import Collection, Profile, Item


# Create your tests here.

User = get_user_model()

# class UserTypeTest(TestCase):
#     def setUp(self):
#         self.user1 = User.objects.create_user(username="patron", password="test")
#         self.user2 = User.objects.create_user(username="librarian", password="test")

#         self.patron = PatronUser.objects.create(user=self.user1, phone_number="0123456789")
#         self.librarian = LibrarianUser.objects.create(user=self.user2, librarian_name="librarian1")
    
#     def test_patron_user_creation(self):
#         self.assertIsNotNone(self.patron)
    
#     def test_patron_user_name(self):
#         self.assertEqual(self.patron.user.username, "patron")

#     def test_patron_user_phone(self):
#         self.assertEqual(self.patron.phone_number, "0123456789")

#     def test_librarian_user_creation(self):
#         self.assertIsNotNone(self.librarian)

#     def test_librarian_user_name(self):
#         self.assertEqual(self.librarian.user.username, "librarian")
    
#     def test_librarian_user_librarian_name(self):
#         self.assertEqual(self.librarian.librarian_name, "librarian1")

#     def test_users_diff(self):
#         user1_patron = PatronUser.objects.filter(user=self.user1).exists() 
#         user1_librarian = LibrarianUser.objects.filter(user=self.user1).exists() 

#         self.assertFalse(user1_patron and user1_librarian, "no difference between customer and librarian user")
    
#     def test_users_diff_param(self):
#         self.assertNotEqual(self.librarian.is_librarian, self.patron.is_librarian)
        
    
class AuthenticationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="usertest", password="test")

    def valid_authentication(self):
        user = authenticate(username="usertest", password="test")
        self.assertIsNotNone(user)

class EditCollectionTests(TestCase):
    
    def setUp(self):
        # Create users
        self.librarian_user = User.objects.create_user(username='librarian', password='password')
        self.non_librarian_user = User.objects.create_user(username='user', password='password')

        # Create profiles, ensuring no duplicates
        self.librarian_profile, _ = Profile.objects.get_or_create(user=self.librarian_user, defaults={'is_librarian': True})
        self.non_librarian_profile, _ = Profile.objects.get_or_create(user=self.non_librarian_user, defaults={'is_librarian': False})
        
        # Create an item
        self.item = Item.objects.create(
            title="Test Item", 
            location="Test Location", 
            condition="Good", 
            status="checked_in"
        )

        # Create a collection with a creator
        self.collection = Collection.objects.create(
            title="Test Collection", 
            creator=self.librarian_profile
        )
        
        # Add the collection's item
        self.collection.items.add(self.item)

    def test_librarian_can_edit_collection(self):
        self.client.login(username='librarian', password='password')
        response = self.client.get(reverse('gearshare:edit_collection', args=[self.collection.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Collection")

    def test_non_librarian_cannot_edit_others_collection(self):
        self.client.login(username='user', password='password')
        response = self.client.get(reverse('gearshare:edit_collection', args=[self.collection.id]))
        self.assertEqual(response.status_code, 403)

    def test_non_librarian_can_edit_own_collection(self):
        # Create a new collection for the non-librarian user
        non_librarian_owner, _ = Profile.objects.get_or_create(user=self.non_librarian_user, defaults={'is_librarian': False})
        new_collection = Collection.objects.create(title="New Collection", creator=non_librarian_owner)
        
        self.client.login(username='user', password='password')
        response = self.client.get(reverse('gearshare:edit_collection', args=[new_collection.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Collection")

    def test_allowed_users_only_non_librarians_and_excludes_creator(self):
        # Add non-librarian users to the allowed_users list, excluding the creator
        non_librarian_users = Profile.objects.filter(is_librarian=False).exclude(id=self.collection.creator.id)
        self.client.login(username='librarian', password='password')
        response = self.client.get(reverse('gearshare:edit_collection', args=[self.collection.id]))
        
        # Make sure only non-librarians and not the creator can be selected
        form = response.context['form']
        allowed_users_choices = form.fields['allowed_users'].queryset

        # Compare the string representation of allowed users with non-librarian users
        self.assertEqual(
            list(allowed_users_choices.values_list('real_name', flat=True)) + list(allowed_users_choices.values_list('email', flat=True)),
            list(non_librarian_users.values_list('real_name', flat=True)) + list(non_librarian_users.values_list('email', flat=True))
        )

    def test_add_item_to_collection(self):
        # Test adding items to the collection
        self.client.login(username='librarian', password='password')
        response = self.client.post(reverse('gearshare:edit_collection', args=[self.collection.id]), {
            'form_type': 'add_items',
            'add_items': [self.item.id]
        })
        self.assertRedirects(response, reverse('gearshare:edit_collection', args=[self.collection.id]))
        self.assertIn(self.item, self.collection.items.all())

    def test_remove_item_from_collection(self):
        # Test removing items from the collection
        self.client.login(username='librarian', password='password')
        response = self.client.post(reverse('gearshare:edit_collection', args=[self.collection.id]), {
            'form_type': 'remove_item',
            'remove_item_id': self.item.id
        })
        self.assertRedirects(response, reverse('gearshare:edit_collection', args=[self.collection.id]))
        self.assertNotIn(self.item, self.collection.items.all())
    
    def test_non_creator_cannot_add_remove_items(self):
        # Non-creator should not be able to add or remove items from the collection
        self.client.login(username='user', password='password')
        response = self.client.post(reverse('gearshare:edit_collection', args=[self.collection.id]), {
            'form_type': 'add_items',
            'add_items': [self.item.id]
        })
        self.assertEqual(response.status_code, 403)

    def test_public_collection_is_public_by_default(self):
        self.client.login(username='librarian', password='password')
        response = self.client.get(reverse('gearshare:edit_collection', args=[self.collection.id]))
        form = response.context['form']
        self.assertTrue(form.initial['is_public'])
    
    def test_private_collection_when_non_librarian_edit(self):
        self.client.login(username='user', password='password')
        response = self.client.post(reverse('gearshare:edit_collection', args=[self.collection.id]), {
            'form_type': 'edit_details',
            'title': self.collection.title,
            'is_public': False
        })
        
        # A non-librarian cannot make the collection private, expect a 403 Forbidden
        self.assertEqual(response.status_code, 403)

        # Ensure the collection's privacy setting did not change
        self.collection.refresh_from_db()
        self.assertTrue(self.collection.is_public)  # The collection should remain public

    def test_creator_can_toggle_is_public(self):
        self.client.login(username='librarian', password='password')
        response = self.client.post(reverse('gearshare:edit_collection', args=[self.collection.id]), {
            'form_type': 'edit_details',
            'title': self.collection.title,
            'is_public': False
        })
        self.assertRedirects(response, reverse('gearshare:view_collection', args=[self.collection.id]))
        self.collection.refresh_from_db()
        self.assertFalse(self.collection.is_public)