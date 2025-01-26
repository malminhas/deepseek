import pytest # type: ignore
import requests # type: ignore
import os
from typing import Generator
import time

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_TIMEOUT = 10  # seconds

@pytest.fixture(scope="session", autouse=True)
def check_api_key() -> None:
    """Ensure DEEPSEEK_API_KEY is set before running tests"""
    assert os.getenv("DEEPSEEK_API_KEY"), "DEEPSEEK_API_KEY environment variable must be set"

@pytest.fixture(scope="session", autouse=True)
def wait_for_api() -> None:
    """Wait for API to be ready"""
    start_time = time.time()
    while time.time() - start_time < TEST_TIMEOUT:
        try:
            requests.get(f"{BASE_URL}/docs")
            return  # API is ready
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)
    pytest.fail("API failed to start")

class TestCompletionEndpoint:
    """Tests for the /completion endpoint"""

    def test_basic_completion(self) -> None:
        """Test basic completion request"""
        response = requests.post(
            f"{BASE_URL}/completion",
            json={
                "prompt": "What is Python?",
                "max_tokens": 100,
                "temperature": 0.7
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "completion" in data
        assert isinstance(data["completion"], str)
        assert len(data["completion"]) > 0

    def test_empty_prompt(self) -> None:
        """Test empty prompt handling"""
        response = requests.post(
            f"{BASE_URL}/completion",
            json={
                "prompt": "",
                "max_tokens": 100,
                "temperature": 0.7
            }
        )
        
        assert response.status_code == 422  # FastAPI validation error

    def test_long_prompt(self) -> None:
        """Test long prompt handling"""
        response = requests.post(
            f"{BASE_URL}/completion",
            json={
                "prompt": "What is Python? " * 100,  # Long prompt
                "max_tokens": 100,
                "temperature": 0.7
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "completion" in data
        assert isinstance(data["completion"], str)

    def test_invalid_temperature(self) -> None:
        """Test temperature validation"""
        response = requests.post(
            f"{BASE_URL}/completion",
            json={
                "prompt": "What is Python?",
                "max_tokens": 100,
                "temperature": 2.0  # Invalid temperature
            }
        )
        
        assert response.status_code == 422  # FastAPI validation error

    def test_invalid_max_tokens(self) -> None:
        """Test max_tokens validation"""
        response = requests.post(
            f"{BASE_URL}/completion",
            json={
                "prompt": "What is Python?",
                "max_tokens": -1,  # Invalid token count
                "temperature": 0.7
            }
        )
        
        assert response.status_code == 422  # FastAPI validation error

    def test_missing_prompt(self) -> None:
        """Test missing prompt handling"""
        response = requests.post(
            f"{BASE_URL}/completion",
            json={
                "max_tokens": 100,
                "temperature": 0.7
            }
        )
        
        assert response.status_code == 422  # FastAPI validation error

    def test_default_parameters(self) -> None:
        """Test default parameters work"""
        response = requests.post(
            f"{BASE_URL}/completion",
            json={
                "prompt": "What is Python?"
                # Omitting optional parameters
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "completion" in data
        assert isinstance(data["completion"], str)

    def test_concurrent_requests(self) -> None:
        """Test handling multiple concurrent requests"""
        import concurrent.futures

        def make_request() -> requests.Response:
            return requests.post(
                f"{BASE_URL}/completion",
                json={"prompt": "What is Python?"}
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            responses = [f.result() for f in futures]

        assert all(r.status_code == 200 for r in responses)
        assert all("completion" in r.json() for r in responses)

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 