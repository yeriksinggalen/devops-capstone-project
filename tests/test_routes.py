"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv("DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(BASE_URL, json=account.serialize(), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(BASE_URL, json=account.serialize(), content_type="test/html")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_list_accounts_api(self):
        """It should list created accounts."""
        self._create_accounts(3)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.get_json()), 3)

    def test_list_accounts_empty_api(self):
        """It should return an empty account list."""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    def test_filter_accounts_by_name_api(self):
        """It should filter accounts by name."""
        account = self._create_accounts(1)[0]
        response = self.client.get(BASE_URL, query_string={"name": account.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.get_json()), 1)

    def test_read_account_api(self):
        """It should read an account by ID."""
        account = self._create_accounts(1)[0]
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["id"], account.id)

    def test_update_account_api(self):
        """It should update an account."""
        account = self._create_accounts(1)[0]
        payload = account.serialize()
        payload["name"] = "Updated Customer"
        response = self.client.put(f"{BASE_URL}/{account.id}", json=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["name"], "Updated Customer")
        self.assertEqual(response.get_json()["id"], account.id)

    def test_delete_account_api(self):
        """It should delete an account."""
        account = self._create_accounts(1)[0]
        response = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_account_api(self):
        """Missing accounts should return 404."""
        account_id = 999999
        response = self.client.get(f"{BASE_URL}/{account_id}")
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(f"{BASE_URL}/{account_id}")
        self.assertEqual(response.status_code, 404)
        response = self.client.put(
            f"{BASE_URL}/{account_id}", json={"name": "Example", "email": "example@example.com", "address": "Jakarta"}
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_update_media_type_api(self):
        """Update should reject non-JSON content."""
        account = self._create_accounts(1)[0]
        response = self.client.put(f"{BASE_URL}/{account.id}", data="invalid", content_type="text/plain")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_invalid_update_body_api(self):
        """Update should reject incomplete account data."""
        account = self._create_accounts(1)[0]
        response = self.client.put(f"{BASE_URL}/{account.id}", json={"name": "Incomplete"})
        self.assertEqual(response.status_code, 400)

    def test_create_location_header_api(self):
        """Create should return the new account URL."""
        account = AccountFactory()
        response = self.client.post(BASE_URL, json=account.serialize())
        self.assertEqual(response.status_code, 201)
        account_id = response.get_json()["id"]
        location = response.headers.get("Location", "")
        self.assertTrue(location.endswith(f"{BASE_URL}/{account_id}"))

    def test_method_not_allowed_api(self):
        """It should return HTTP 405 for invalid methods."""
        response = self.client.post("/health")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["error"], "Method not Allowed")

    def test_internal_server_error_api(self):
        """It should handle an unexpected server error."""
        from unittest.mock import patch

        previous = app.config.get("PROPAGATE_EXCEPTIONS")
        app.config["PROPAGATE_EXCEPTIONS"] = False

        try:
            with patch("service.routes.Account.all", side_effect=RuntimeError("Simulated failure")):
                response = self.client.get(BASE_URL)
        finally:
            app.config["PROPAGATE_EXCEPTIONS"] = previous

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"], "Internal Server Error")

    def test_security_headers(self):
        """It should return the Talisman security headers."""
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("X-Frame-Options"),
            "SAMEORIGIN"
        )
        self.assertEqual(
            response.headers.get("X-Content-Type-Options"),
            "nosniff"
        )
        self.assertIn(
            "default-src",
            response.headers.get("Content-Security-Policy", "")
        )

    def test_cors_headers(self):
        """It should allow cross-origin requests."""
        response = self.client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "*"
        )
