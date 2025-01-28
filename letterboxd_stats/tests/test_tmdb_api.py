from unittest.mock import patch

import pytest

from letterboxd_stats.cli.tmdb_api import TMDbAPI


@pytest.fixture
def tmdb_api():
    """Fixture for initializing the TMDbAPI with a test API key."""
    return TMDbAPI(api_key="test_api_key")

@patch("requests.get")
def test_search_movie_success(mock_get, tmdb_api):
    """Test successful movie search."""
    mock_get.return_value.json.return_value = {
        "results": [{"id": 1, "title": "Inception"}]
    }
    result = tmdb_api.search_movie("Inception")
    assert result["results"][0]["title"] == "Inception"
    mock_get.assert_called_once_with(
        "https://api.themoviedb.org/3/search/movie",
        params={"api_key": "test_api_key", "query": "Inception"}
    )

@patch("requests.get")
def test_get_movie_details_success(mock_get, tmdb_api):
    """Test fetching movie details."""
    mock_get.return_value.json.return_value = {
        "id": 1, "title": "Inception", "release_date": "2010-07-16"
    }
    result = tmdb_api.get_movie_details(1)
    assert result["title"] == "Inception"
    assert result["release_date"] == "2010-07-16"
    mock_get.assert_called_once_with(
        "https://api.themoviedb.org/3/movie/1",
        params={"api_key": "test_api_key"}
    )

@patch("requests.get")
def test_search_movie_invalid_api_key(mock_get, tmdb_api):
    """Test search_movie with an invalid API key."""
    mock_get.return_value.json.return_value = {
        "status_code": 401,
        "status_message": "Invalid API key"
    }
    result = tmdb_api.search_movie("Inception")
    assert result["status_code"] == 401
    assert result["status_message"] == "Invalid API key"

def test_search_movie_empty_query(tmdb_api):
    """Test search_movie with an empty query."""
    with pytest.raises(ValueError, match="Query must not be empty"):
        tmdb_api.search_movie("")
