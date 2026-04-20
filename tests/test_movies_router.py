import pytest
import random
import string
from httpx import AsyncClient, ASGITransport
from main import app

def get_random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

@pytest.fixture
async def test_user():
    username = "movie_user_" + get_random_string()
    password = "SecurePassword123!"
    email = f"{username}@test.com"
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register
        await client.post(
            "/users",
            json={
                "username": username,
                "password": password,
                "email": email,
            },
        )
        # Login
        login_res = await client.post(
            "/login", data={"username": username, "password": password}
        )
        token = login_res.json()["access_token"]
        return {"username": username, "token": token}

@pytest.mark.asyncio
async def test_movies_workflow(test_user):
    """
    Test the full workflow: search -> add -> get -> favorite -> delete.
    """
    token = test_user["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Search (Public)
        search_res = await client.get("/movies/search?query=Inception", headers=headers)
        assert search_res.status_code == 200
        results = search_res.json()["data"]["results"]
        assert len(results) > 0
        movie_to_add = results[0]

        # 2. Add Movie
        add_res = await client.post(
            "/movies/",
            headers=headers,
            json={
                "query": movie_to_add["title"],
                "tmdb_id": movie_to_add["tmdb_id"]
            }
        )
        assert add_res.status_code == 200
        assert add_res.json()["success"] is True

        # 3. Get Collection
        get_res = await client.get("/movies/", headers=headers)
        assert get_res.status_code == 200
        watched = get_res.json()["data"]["watched_movies"]
        assert len(watched) > 0
        added_movie = watched[0]
        assert added_movie["tmdb_id"] == movie_to_add["tmdb_id"]

        # 4. Toggle Favorite
        fav_res = await client.post(f"/movies/{added_movie['id']}/favorite", headers=headers)
        assert fav_res.status_code == 200
        assert fav_res.json()["is_favorite"] is True

        # 5. Get Recommendations
        rec_res = await client.get("/movies/recommendations", headers=headers)
        assert rec_res.status_code == 200
        recs = rec_res.json()["data"]["recommendations"]
        assert isinstance(recs, list)

        # 6. Delete Movie
        del_res = await client.delete(f"/movies/{added_movie['id']}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # 7. Verify deletion
        get_res_after = await client.get("/movies/", headers=headers)
        assert len(get_res_after.json()["data"]["watched_movies"]) == 0

@pytest.mark.asyncio
async def test_movies_unauthorized(test_user):
    """
    Verify that accessing endpoints without a token returns 401.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/movies/")
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_old_paths_return_404(test_user):
    """
    Verify that the old paths (with username) no longer exist.
    """
    token = test_user["token"]
    username = test_user["username"]
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/movies/{username}", headers=headers)
        assert res.status_code in [404, 405]
