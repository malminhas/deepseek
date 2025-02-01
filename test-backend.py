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

class TestModelEndpoints:
    """Tests for the model configuration endpoints"""

    def test_get_default_model(self) -> None:
        """Test getting default model"""
        response = requests.get(f"{BASE_URL}/model")
        assert response.status_code == 200
        data = response.json()
        assert "model" in data
        assert data["model"] in ["deepseek-chat", "deepseek-reasoner"]

    def test_set_model(self) -> None:
        """Test setting model"""
        # Set to reasoner
        response = requests.put(
            f"{BASE_URL}/model",
            json={"model": "deepseek-reasoner"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "deepseek-reasoner"

        # Verify get returns new model
        response = requests.get(f"{BASE_URL}/model")
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "deepseek-reasoner"

        # Set back to chat
        response = requests.put(
            f"{BASE_URL}/model",
            json={"model": "deepseek-chat"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "deepseek-chat"

    def test_invalid_model(self) -> None:
        """Test setting invalid model"""
        response = requests.put(
            f"{BASE_URL}/model",
            json={"model": "invalid-model"}
        )
        assert response.status_code == 422  # Validation error

    def test_completion_with_different_models(self) -> None:
        """Test completions work with both models"""
        models = ["deepseek-chat", "deepseek-reasoner"]
        
        for model in models:
            # Set model
            requests.put(f"{BASE_URL}/model", json={"model": model})
            
            # Test completion
            response = requests.post(
                f"{BASE_URL}/completion",
                json={"prompt": "What is Python?"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "completion" in data
            assert isinstance(data["completion"], str)
            assert len(data["completion"]) > 0

@pytest.mark.asyncio
async def test_perplexity_completion():
    """Test completion with Perplexity Sonar model"""
    # Set model to Perplexity
    response = await client.put("/model", json={"model": "sonar"})
    assert response.status_code == 200
    assert response.json()["model"] == "sonar"
    
    # Test completion
    response = await client.post(
        "/completion",
        json={
            "prompt": "What is 2+2?",
            "max_tokens": 100,
            "temperature": 0.7
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "completion" in data
    assert isinstance(data["completion"], str)
    assert len(data["completion"]) > 0

@pytest.mark.asyncio
async def test_perplexity_missing_api_key(monkeypatch):
    """Test error handling when Perplexity API key is missing"""
    # Set model to Perplexity
    response = await client.put("/model", json={"model": "sonar"})
    assert response.status_code == 200
    
    # Remove API key
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    
    response = await client.post(
        "/completion",
        json={
            "prompt": "Test prompt",
            "max_tokens": 100,
            "temperature": 0.7
        }
    )
    
    assert response.status_code == 500
    assert "PERPLEXITY_API_KEY environment variable must be set" in response.json()["detail"]

@pytest.mark.asyncio
async def test_perplexity_timeout():
    """Test timeout handling for Perplexity API"""
    # Set model to Perplexity
    response = await client.put("/model", json={"model": "sonar"})
    assert response.status_code == 200
    
    # Test with a long prompt
    response = await client.post(
        "/completion",
        json={
            "prompt": "Please explain " + "very detailed " * 100,
            "max_tokens": 100,
            "temperature": 0.7
        }
    )
    
    # Either succeeds or times out gracefully
    if response.status_code == 504:
        assert "timed out" in response.json()["detail"].lower()
    else:
        assert response.status_code == 200
        assert "completion" in response.json()

@pytest.mark.asyncio
async def test_ollama_completion():
    """Test completion with Ollama deepseek model"""
    # Set model to Ollama
    response = await client.put("/model", json={"model": "ollama-deepseek"})
    assert response.status_code == 200
    assert response.json()["model"] == "ollama-deepseek"
    
    # Test completion
    response = await client.post(
        "/completion",
        json={
            "prompt": "What is 2+2?",
            "max_tokens": 100,
            "temperature": 0.7
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "completion" in data
    assert isinstance(data["completion"], str)
    assert len(data["completion"]) > 0

@pytest.mark.asyncio
async def test_ollama_timeout():
    """Test timeout handling for Ollama API"""
    # Set model to Ollama
    response = await client.put("/model", json={"model": "ollama-deepseek"})
    assert response.status_code == 200
    
    # Test with a long prompt
    response = await client.post(
        "/completion",
        json={
            "prompt": "Please explain " + "very detailed " * 100,
            "max_tokens": 100,
            "temperature": 0.7
        }
    )
    
    # Either succeeds or times out gracefully
    if response.status_code == 504:
        assert "timed out" in response.json()["detail"].lower()
    else:
        assert response.status_code == 200
        assert "completion" in response.json()

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 