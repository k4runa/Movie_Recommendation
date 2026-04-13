from fastapi.testclient import TestClient
from main import app
from services.deps import users_manager

client = TestClient(app)

def test_register_and_login():
    # Cleanup leftover test data if exists
    try:
        users_manager.delete_user("pytes_user")
    except:
        pass
        
    # Test registration
    register_res = client.post("/users", json={
        "username": "pytes_user",
        "password": "secure123",
        "email": "pytes@test.com"
    })
    # Might already exist if DB wasnt wiped, but assuming clean DB or deletion succeeded
    if register_res.status_code != 409:
        assert register_res.status_code == 200
        assert register_res.json()["success"] == True
    
    # Test login
    login_res = client.post("/login", data={
        "username": "pytes_user",
        "password": "secure123"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
    
    token = login_res.json()["access_token"]
    
    # Test accessing own protected route
    user_res = client.get(
        "/users/pytes_user",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert user_res.status_code == 200
    assert user_res.json()["data"]["user"]["username"] == "pytes_user"
    
    # Test accessing someone else's protected route
    other_res = client.get(
        "/users/admin",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert other_res.status_code == 403
    
    # Cleanup
    try:
        users_manager.delete_user("pytes_user")
    except:
        pass
