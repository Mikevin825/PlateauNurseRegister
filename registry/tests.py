from django.conf import settings
from django.test import TestCase


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Plateau State Nurse Registry")
        self.assertContains(response, "Registration and licence verification")

    def test_debug_defaults_to_false(self):
        self.assertFalse(settings.DEBUG)
