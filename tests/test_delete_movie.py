"""
tests/test_delete_movie.py — Unit Tests for MovieManager.delete_movie

Validates the refactored delete_movie method that uses database movie_id
instead of TMDB title search.

Scenarios:
    1. User not found → UserNotFoundError
    2. Movie not in user's list → MovieNotFoundError
    3. Happy path → movie deleted from session

Run with:
    python -m pytest tests/test_delete_movie.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from services.database import (
    MovieManager,
    MovieNotFoundError,
    UserNotFoundError,
)


def make_execute_result(return_val):
    """Helper: mock result whose .scalar_one_or_none() returns the given value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_val
    return result


class TestDeleteMovie:
    """Tests for MovieManager.delete_movie (ID-based, no TMDB dependency)."""

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self):
        """If the user doesn't exist, UserNotFoundError should be raised."""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=make_execute_result(None))

        manager = MovieManager.__new__(MovieManager)

        with pytest.raises(UserNotFoundError):
            await MovieManager.delete_movie.__wrapped__(
                manager, session, "ghost_user", 42
            )

    @pytest.mark.asyncio
    async def test_movie_not_found_raises(self):
        """If the movie_id doesn't belong to this user → MovieNotFoundError."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                make_execute_result(mock_user),  # user found
                make_execute_result(None),        # movie NOT found
            ]
        )

        manager = MovieManager.__new__(MovieManager)

        with pytest.raises(MovieNotFoundError):
            await MovieManager.delete_movie.__wrapped__(
                manager, session, "testuser", 999
            )

    @pytest.mark.asyncio
    async def test_happy_path_deletes_movie(self):
        """Happy path: movie exists and belongs to user → session.delete called."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"

        mock_movie = MagicMock()
        mock_movie.id = 42
        mock_movie.user_id = 1
        mock_movie.title = "Fight Club"

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                make_execute_result(mock_user),   # user found
                make_execute_result(mock_movie),  # movie found
            ]
        )
        session.delete = AsyncMock()

        manager = MovieManager.__new__(MovieManager)

        result = await MovieManager.delete_movie.__wrapped__(
            manager, session, "testuser", 42
        )

        assert result is True
        session.delete.assert_called_once_with(mock_movie)

    @pytest.mark.asyncio
    async def test_no_tmdb_call_made(self):
        """Verify that no TMDB API call is made during deletion."""
        mock_user = MagicMock()
        mock_user.id = 1

        mock_movie = MagicMock()
        mock_movie.id = 42
        mock_movie.user_id = 1
        mock_movie.title = "Test"

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                make_execute_result(mock_user),
                make_execute_result(mock_movie),
            ]
        )
        session.delete = AsyncMock()

        manager = MovieManager.__new__(MovieManager)

        # Patch fetch_tmdb_data to raise if it's ever called
        from unittest.mock import patch
        with patch("services.database.fetch_tmdb_data", side_effect=AssertionError("TMDB should not be called")):
            result = await MovieManager.delete_movie.__wrapped__(
                manager, session, "testuser", 42
            )

        assert result is True
