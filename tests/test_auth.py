
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

# ---------------------------------------------------------------------------
# Test Constants
# ---------------------------------------------------------------------------
import random
import string

def get_random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

TEST_USERNAME = "user_" + get_random_string()
TEST_PASSWORD = "SecurePassword123!"
TEST_EMAIL = TEST_USERNAME + "@test.com"


@pytest.mark.asyncio
async def test_register_and_login():
    """
    Full lifecycle test: register → login → access own route → verify
    that accessing another user's route is forbidden.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # -------------------------------------------------------------------
        # Step 1: Register a new user
        # -------------------------------------------------------------------
        register_res = await client.post(
            "/users",
            json={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "email": TEST_EMAIL,
            },
        )
        # If the user already exists (DB wasn't wiped), skip the assertion
        if register_res.status_code != 409:
            assert register_res.status_code == 200
            assert register_res.json()["success"] == True

        # -------------------------------------------------------------------
        # Step 2: Login and obtain a JWT
        # -------------------------------------------------------------------
        login_res = await client.post(
            "/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        assert token is not None

        # -------------------------------------------------------------------
        # Step 3: Access protected route (/users/me)
        # -------------------------------------------------------------------
        me_res = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["data"]["user"]["username"] == TEST_USERNAME

        # -------------------------------------------------------------------
        # Step 4: Verify that path-based access is gone → 404 or 405
        # -------------------------------------------------------------------
        other_res = await client.get("/users/admin", headers={"Authorization": f"Bearer {token}"})
        assert other_res.status_code in [404, 405]

        # -------------------------------------------------------------------
        # Teardown: Soft-delete the test user via HTTP (using new path)
        # -------------------------------------------------------------------
        del_res = await client.delete("/users/", headers={"Authorization": f"Bearer {token}"})
        assert del_res.status_code == 200
