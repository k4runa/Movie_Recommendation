"""
tests/test_update_status.py — Unit Tests for MovieManager.update_status

Validates the fixed logic for marking a tracked movie as 'Watched'.

Scenarios:
    1. User not found → UserNotFoundError
    2. Movie NOT in user's tracked list → MovieNotFoundError
    3. Movie already has a WatchedMovies entry → MovieAlreadyExists
    4. Happy path → WatchedMovies record created, status updated

Run with:
    python -m pytest tests/test_update_status.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.database import (
    MovieManager,
    MovieNotFoundError,
    MovieAlreadyExists,
    UserNotFoundError,
)

FAKE_TMDB_DATA = {
    "tmdb_id": 550,
    "title": "Fight Club",
    "overview": "An insomniac office worker...",
    "genre_ids": "18,53",
    "vote_average": "8.4",
}


def make_execute_result(return_val):
    """Helper: create a mock result whose .scalar_one_or_none() returns the given value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_val
    return result


def make_mock_user(user_id=1, username="testuser"):
    user = MagicMock()
    user.id = user_id
    user.username = username
    return user


def make_mock_movie(movie_id=42, user_id=1, tmdb_id=550, title="Fight Club"):
    movie = MagicMock()
    movie.id = movie_id
    movie.user_id = user_id
    movie.tmdb_id = tmdb_id
    movie.title = title
    movie.status = "Not yet"
    return movie


async def fake_fetch_tmdb_data(query: str):
    return FAKE_TMDB_DATA


# ---------------------------------------------------------------------------
# Tests — call __wrapped__ directly to bypass the @transaction decorator
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    """Tests for MovieManager.update_status after the logic inversion fix."""

    @pytest.mark.asyncio
    @patch("services.database.fetch_tmdb_data", side_effect=fake_fetch_tmdb_data)
    async def test_user_not_found_raises(self, mock_fetch):
        """If the user doesn't exist, UserNotFoundError should be raised."""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=make_execute_result(None))

        manager = MovieManager.__new__(MovieManager)
        manager.session = MagicMock()
        manager.session.return_value.__aenter__.return_value = session
    
        with pytest.raises(UserNotFoundError):
            await manager.update_status("ghost_user", "Watched", "Fight Club")

    @pytest.mark.asyncio
    @patch("services.database.fetch_tmdb_data", side_effect=fake_fetch_tmdb_data)
    async def test_movie_not_tracked_raises(self, mock_fetch):
        """If the movie is NOT in the user's tracked list → MovieNotFoundError."""
        mock_user = make_mock_user()

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                make_execute_result(mock_user),  # user found
                make_execute_result(None),        # movie NOT tracked
            ]
        )

        manager = MovieManager.__new__(MovieManager)
        manager.session = MagicMock()
        manager.session.return_value.__aenter__.return_value = session
    
        with pytest.raises(MovieNotFoundError):
            await manager.update_status("testuser", "Watched", "Fight Club")

    @pytest.mark.asyncio
    @patch("services.database.fetch_tmdb_data", side_effect=fake_fetch_tmdb_data)
    async def test_already_watched_raises(self, mock_fetch):
        """If a WatchedMovies entry already exists → MovieAlreadyExists."""
        mock_user = make_mock_user()
        mock_movie = make_mock_movie()

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                make_execute_result(mock_user),       # user found
                make_execute_result(mock_movie),      # movie IS tracked
                make_execute_result(MagicMock()),     # already watched entry exists
            ]
        )

        manager = MovieManager.__new__(MovieManager)
        manager.session = MagicMock()
        manager.session.return_value.__aenter__.return_value = session
    
        with pytest.raises(MovieAlreadyExists):
            await manager.update_status("testuser", "Watched", "Fight Club")

    @pytest.mark.asyncio
    @patch("services.database.fetch_tmdb_data", side_effect=fake_fetch_tmdb_data)
    async def test_happy_path_creates_watched_entry(self, mock_fetch):
        """Happy path: movie is tracked, not yet watched → creates WatchedMovies, returns True."""
        mock_user = make_mock_user()
        mock_movie = make_mock_movie()

        session = AsyncMock()
        session.add = MagicMock()
        session.execute = AsyncMock(
            side_effect=[
                make_execute_result(mock_user),       # user found
                make_execute_result(mock_movie),      # movie IS tracked
                make_execute_result(None),            # NOT yet watched
            ]
        )

        manager = MovieManager.__new__(MovieManager)
        manager.session = MagicMock()
        manager.session.return_value.__aenter__.return_value = session
        session.commit = AsyncMock()
    
        result = await manager.update_status("testuser", "Watched", "Fight Club")
    
        assert result is True
        assert mock_movie.status == "Watched"
        session.add.assert_called_once()
        session.commit.assert_called_once()
