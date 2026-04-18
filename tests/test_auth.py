"""
tests/test_auth.py — End-to-End Authentication Tests

Validates the full authentication lifecycle:
    1. User registration    (POST /users)
    2. User login           (POST /login)
    3. Protected route access with a valid token
    4. Ownership enforcement (accessing another user → 403)

Run with:
    python -m pytest tests/ -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app

# ---------------------------------------------------------------------------
# Test Constants
# ---------------------------------------------------------------------------
TEST_USERNAME = "pytes_user"
TEST_PASSWORD = "secure123"
TEST_EMAIL = "pytes@test.com"


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
        assert "access_token" in login_res.json()

        token = login_res.json()["access_token"]

        # -------------------------------------------------------------------
        # Step 3: Access own protected profile route
        # -------------------------------------------------------------------
        user_res = await client.get(
            f"/users/{TEST_USERNAME}", headers={"Authorization": f"Bearer {token}"}
        )
        assert user_res.status_code == 200
        assert user_res.json()["data"]["user"]["username"] == TEST_USERNAME

        # -------------------------------------------------------------------
        # Step 4: Verify ownership enforcement — accessing another user → 403
        # -------------------------------------------------------------------
        other_res = await client.get("/users/admin", headers={"Authorization": f"Bearer {token}"})
        assert other_res.status_code == 403

        # -------------------------------------------------------------------
        # Teardown: Soft-delete the test user via HTTP
        # -------------------------------------------------------------------
        await client.delete(
            f"/users/{TEST_USERNAME}",
            headers={"Authorization": f"Bearer {token}"},
        )
