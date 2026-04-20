
import pytest
from httpx import AsyncClient, ASGITransport
from main import app
import asyncio

@pytest.mark.asyncio
async def test_dm_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create two users
        import uuid
        uid = str(uuid.uuid4())[:8]
        user1 = {"username": f"dm_user1_{uid}", "password": "SecurePassword123!", "email": f"dm1_{uid}@test.com"}
        user2 = {"username": f"dm_user2_{uid}", "password": "SecurePassword123!", "email": f"dm2_{uid}@test.com"}
        
        await client.post("/users", json=user1)
        await client.post("/users", json=user2)
        
        # 2. Login both
        login1 = await client.post("/login", data={"username": f"dm_user1_{uid}", "password": "SecurePassword123!"})
        token1 = login1.json()["access_token"]
        
        login2 = await client.post("/login", data={"username": f"dm_user2_{uid}", "password": "SecurePassword123!"})
        token2 = login2.json()["access_token"]
        
        # Get user2 ID
        me2 = await client.get("/users/me", headers={"Authorization": f"Bearer {token2}"})
        user2_id = me2.json()["data"]["user"]["id"]
        
        # 3. User1 sends message to User2
        msg_payload = {"receiver_id": user2_id, "content": "Hello User2!"}
        send_res = await client.post("/social/message", json=msg_payload, headers={"Authorization": f"Bearer {token1}"})
        assert send_res.status_code == 200
        assert send_res.json()["success"] == True
        
        # 4. User2 checks conversations (Message Requests)
        # Initially it should be in PENDING for User2
        conv_res_pending = await client.get("/social/conversations?status=PENDING", headers={"Authorization": f"Bearer {token2}"})
        assert conv_res_pending.status_code == 200
        pending_convs = conv_res_pending.json()["data"]["conversations"]
        assert len(pending_convs) > 0
        assert pending_convs[0]["participant"]["username"] == user1["username"]
        
        # User1 should see it in ACCEPTED as PENDING_SENT
        conv_res_sent = await client.get("/social/conversations?status=ACCEPTED", headers={"Authorization": f"Bearer {token1}"})
        assert len(conv_res_sent.json()["data"]["conversations"]) > 0
        
        # User2 accepts the request
        me1 = await client.get("/users/me", headers={"Authorization": f"Bearer {token1}"})
        user1_id = me1.json()["data"]["user"]["id"]
        # Corrected: PATCH /social/requests/{id}/accept
        accept_res = await client.patch(f"/social/requests/{user1_id}/accept", headers={"Authorization": f"Bearer {token2}"})
        assert accept_res.status_code == 200
        
        # Now it should be in ACCEPTED for User2
        conv_res = await client.get("/social/conversations", headers={"Authorization": f"Bearer {token2}"})
        assert conv_res.status_code == 200
        conversations = conv_res.json()["data"]["conversations"]
        assert len(conversations) > 0
        assert conversations[0]["participant"]["username"] == user1["username"]
        assert conversations[0]["unread_count"] == 1
        
        # 5. User2 reads messages
        history_res = await client.get(f"/social/messages/{user1_id}", headers={"Authorization": f"Bearer {token2}"})
        assert history_res.status_code == 200
        messages = history_res.json()["data"]["messages"]
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello User2!"
        
        # 6. User2 marks as read
        read_res = await client.patch(f"/social/messages/{user1_id}/read", headers={"Authorization": f"Bearer {token2}"})
        assert read_res.status_code == 200
        
        # Check unread count again
        conv_res2 = await client.get("/social/conversations", headers={"Authorization": f"Bearer {token2}"})
        assert conv_res2.json()["data"]["conversations"][0]["unread_count"] == 0
        
        # 7. User1 deletes conversation
        del_res = await client.delete(f"/social/conversation/{user2_id}", headers={"Authorization": f"Bearer {token1}"})
        assert del_res.status_code == 200
        
        # User1 should see 0 conversations
        conv_res3 = await client.get("/social/conversations", headers={"Authorization": f"Bearer {token1}"})
        assert len(conv_res3.json()["data"]["conversations"]) == 0
        
        # User2 should still see the conversation (logical deletion is individual)
        conv_res4 = await client.get("/social/conversations", headers={"Authorization": f"Bearer {token2}"})
        assert len(conv_res4.json()["data"]["conversations"]) == 1
        
        # Cleanup
        await client.delete(f"/users/{user1['username']}", headers={"Authorization": f"Bearer {token1}"})
        await client.delete(f"/users/{user2['username']}", headers={"Authorization": f"Bearer {token2}"})
