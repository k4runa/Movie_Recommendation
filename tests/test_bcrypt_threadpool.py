"""
tests/test_bcrypt_threadpool.py — Verify bcrypt calls don't block the event loop

Validates that bcrypt.hashpw and bcrypt.checkpw in database.py are offloaded
to a threadpool via run_in_threadpool, preventing event loop starvation.

Strategy:
    Patch run_in_threadpool to confirm it is called with bcrypt functions
    as arguments, rather than bcrypt being called directly.

Run with:
    python -m pytest tests/test_bcrypt_threadpool.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.database import UserManager, MovieManager


FAKE_HASH = b"$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfake"


class TestBcryptThreadpool:
    """Ensure bcrypt operations are offloaded to threadpool in database.py."""

    @pytest.mark.asyncio
    @patch("services.database.run_in_threadpool", new_callable=AsyncMock, return_value=FAKE_HASH)
    async def test_add_user_uses_threadpool_for_hashing(self, mock_threadpool):
        """add_user should call run_in_threadpool with bcrypt.hashpw, not bcrypt.hashpw directly."""
        import bcrypt
        from services.schemas import UserScheme

        mock_user_scheme = UserScheme(username="testuser", password="secure123", email="test@test.com")

        # Mock session
        session = AsyncMock()
        session.add = MagicMock()

        # Mock user_exists to return False
        manager = UserManager.__new__(UserManager)
        manager.session = MagicMock()
        manager.user_exists = AsyncMock(return_value=False)

        await UserManager.add_user.__wrapped__(manager, session, mock_user_scheme)

        # Verify run_in_threadpool was called (not raw bcrypt.hashpw)
        mock_threadpool.assert_called_once()
        call_args = mock_threadpool.call_args
        # First positional arg should be bcrypt.hashpw
        assert call_args[0][0] is bcrypt.hashpw, (
            "run_in_threadpool should be called with bcrypt.hashpw as the function"
        )

    @pytest.mark.asyncio
    @patch("services.database.run_in_threadpool", new_callable=AsyncMock)
    async def test_update_password_uses_threadpool(self, mock_threadpool):
        """update_user_field('password') should use run_in_threadpool for both checkpw and hashpw."""
        import bcrypt

        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.password = FAKE_HASH.decode("utf-8")
        mock_user.email = "old@test.com"

        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        session.execute = AsyncMock(return_value=user_result)

        manager = UserManager.__new__(UserManager)

        # First call: checkpw (verify current password) → True
        # Second call: checkpw (same password check) → False
        # Third call: hashpw (hash new password) → fake hash
        mock_threadpool.side_effect = [True, False, FAKE_HASH]

        result = await UserManager.update_user_field.__wrapped__(
            manager, session, "testuser", "password", "new_secure_pass", "current_pass"
        )

        assert result is True
        # Should have 3 threadpool calls: verify, same-check, hash
        assert mock_threadpool.call_count == 3

        # All calls should use bcrypt functions
        calls = mock_threadpool.call_args_list
        assert calls[0][0][0] is bcrypt.checkpw, "First call should verify current password"
        assert calls[1][0][0] is bcrypt.checkpw, "Second call should check same password"
        assert calls[2][0][0] is bcrypt.hashpw, "Third call should hash new password"
