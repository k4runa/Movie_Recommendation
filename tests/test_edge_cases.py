"""
tests/test_edge_cases.py — High-Value Edge Case and Failure Scenarios

This suite validates the robustness of the fixes made in issues #1–#6 by simulating
concurrency issues, invalid inputs, and transaction failures.

Run with:
    python -m pytest tests/test_edge_cases.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.database import MovieManager, UserManager
from sqlalchemy.exc import IntegrityError


class TestHighValueEdgeCases:

    @pytest.mark.asyncio
    async def test_add_user_concurrency_race_condition(self):
        """
        Protects against: Race condition in add_user where two concurrent requests
        bypass the `user_exists` check.
        Why it matters: If the DB unique constraint throws an IntegrityError, the
        @transaction decorator MUST catch it, rollback, and re-raise or the session
        will be left in a broken state, causing subsequent queries to fail (500 errors).
        """
        manager = UserManager.__new__(UserManager)
        manager.user_exists = AsyncMock(return_value=False)  # Bypass manual check
        
        # Mock session to raise IntegrityError on commit
        mock_session_instance = MagicMock() # session.add is synchronous!
        mock_session_instance.add = MagicMock()
        mock_session_instance.commit = AsyncMock(side_effect=IntegrityError("mock error", "mock params", "mock orig"))
        mock_session_instance.rollback = AsyncMock()
        
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__.return_value = mock_session_instance
        manager.session = MagicMock(return_value=mock_session_context)
        
        mock_user = MagicMock()
        mock_user.username = "race_user"
        mock_user.password = "pass123"
        mock_user.email = "race@test.com"
        
        # The transaction decorator should rollback and bubble up the exception
        with pytest.raises(IntegrityError):
            await UserManager.add_user(manager, mock_user) # Call the decorated method!
            
        mock_session_instance.rollback.assert_called_once()


    @pytest.mark.asyncio
    @patch("services.database.run_in_threadpool", new_callable=AsyncMock)
    async def test_update_user_field_privilege_escalation(self, mock_threadpool):
        """
        Protects against: Malicious users trying to update fields like 'role', 'id',
        or 'is_deleted' via the update_user_field endpoint.
        Why it matters: Critical security boundary. Ensures the whitelist is strictly enforced.
        """
        manager = UserManager.__new__(UserManager)
        
        session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = MagicMock(username="testuser")
        session.execute = AsyncMock(return_value=user_result)
        
        with pytest.raises(ValueError, match="cannot be updated"):
            await UserManager.update_user_field.__wrapped__(
                manager, session, "testuser", "role", "admin"
            )


    @pytest.mark.asyncio
    @patch("services.database.run_in_threadpool", new_callable=AsyncMock)
    async def test_update_user_field_wrong_password(self, mock_threadpool):
        """
        Protects against: Account takeover via unauthorized email/password changes.
        Why it matters: Validates the bcrypt offloading logic correctly handles verification failure.
        """
        manager = UserManager.__new__(UserManager)
        
        session = AsyncMock()
        mock_user = MagicMock(username="testuser", password="hashed_pass")
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        session.execute = AsyncMock(return_value=user_result)
        
        # Mock bcrypt.checkpw to return False (invalid password)
        mock_threadpool.return_value = False
        
        with pytest.raises(ValueError, match="Invalid current password"):
            await UserManager.update_user_field.__wrapped__(
                manager, session, "testuser", "email", "hacker@test.com", "wrongpass"
            )


    @pytest.mark.asyncio
    async def test_get_watched_movies_out_of_bounds_pagination(self):
        """
        Protects against: Clients requesting a page far beyond the available records.
        Why it matters: Before the SQL-level pagination fix, this would have sliced an
        empty array but still loaded ALL movies into memory. Now it gracefully returns
        an empty list from the DB query without loading anything.
        """
        manager = MovieManager.__new__(MovieManager)
        
        session = AsyncMock()
        # First execute: user exists. Second execute: empty movies result.
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = 1
        
        movies_result = MagicMock()
        movies_result.scalars().all.return_value = []
        
        session.execute = AsyncMock(side_effect=[user_result, movies_result])
        
        result = await MovieManager.get_watched_movies.__wrapped__(
            manager, session, "testuser", skip=9999, limit=10
        )
        assert result == []


    @pytest.mark.asyncio
    async def test_transaction_decorator_rollback_on_failure(self):
        """
        Protects against: Partial database writes leaving the system in a corrupted state.
        Why it matters: If an exception occurs after session.add() but before commit(),
        the transaction must be rolled back.
        """
        # Create a dummy manager with a mock session factory
        class DummyManager:
            def __init__(self):
                self.mock_session = AsyncMock()
                self.session = MagicMock(return_value=self.mock_session)

            @UserManager.transaction
            async def failing_method(self, session):
                session.add(MagicMock())
                raise RuntimeError("Unexpected failure")

        manager = DummyManager()
        
        with pytest.raises(RuntimeError, match="Unexpected failure"):
            await manager.failing_method()
            
        # Verify rollback was called on the mock session context manager
        # Since self.session() returns a context manager, we need to inspect its __aenter__ return value
        mock_session_instance = manager.mock_session.__aenter__.return_value
        mock_session_instance.rollback.assert_called_once()
        mock_session_instance.commit.assert_not_called()
