"""
Search Backend API Service
---------------------------

A FastAPI backend service that integrates with the Deepseek API for text completions.

This service provides a single endpoint that accepts text prompts and returns
AI-generated completions using the Deepseek language model.

Version History:
    1.0.0 - (Latest Release) - 26.01.25
        - Added Deepseek API integration

        
Installation:
    pip install fastapi uvicorn httpx pydantic

Environment Variables:
    DEEPSEEK_API_KEY: Your Deepseek API key (required)

Running the service:
    Development with hot reload:
        uvicorn search-backend:app --reload --host 0.0.0.0 --port 8001
    
    Production:
        uvicorn search-backend:app --host 0.0.0.0 --port 8001

Dependencies:
    - FastAPI
    - uvicorn (for serving)
    - pydantic (for data validation)

Documentation:
    Swagger UI: http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc

Endpoints:
    POST /completion: Generate text completion from a prompt

License: MIT
"""

from fastapi import FastAPI, HTTPException # type: ignore
from pydantic import BaseModel, Field, validator # type: ignore
from openai import OpenAI # type: ignore
import os
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware # type: ignore
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

VERSION = "1.0.0"
AUTHOR = "Mal Minhas"
RELEASE_DATE = "26.01.2025"
LICENSE = "MIT"

app = FastAPI(
    title="Search API",
    description="Backend service for Deepseek text completions",
    version=VERSION,
    author=AUTHOR,
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": LICENSE,
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only. In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/beta/completions"

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

def configure_logging():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    global logger
    logger = logging.getLogger("search-api")

    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        "logs/search-api.log",
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )

    # Create formatters and add it to handlers
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

configure_logging()

class PromptRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="The text prompt to send to the Deepseek API",
        example="Write a function that calculates fibonacci numbers",
        min_length=1  # Add minimum length validation
    )
    max_tokens: Optional[int] = Field(
        default=1000,
        description="Maximum number of tokens to generate in the response",
        ge=1,
        le=4096,
        example=1000
    )
    temperature: Optional[float] = Field(
        default=0.7,
        description="Controls randomness in the response. Higher values make output more random, lower values make it more deterministic",
        ge=0.0,
        le=1.0,
        example=0.7
    )

    @validator('prompt')
    def prompt_not_empty(cls, v):
        """Validate that prompt is not just whitespace"""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or just whitespace")
        return v

class CompletionResponse(BaseModel):
    completion: str = Field(
        ...,
        description="The generated text completion from Deepseek API",
        example="Here's a Python function to calculate Fibonacci numbers:\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
    )

@app.post(
    "/completion",
    response_model=CompletionResponse,
    summary="Get AI text completion",
    description="""
    Sends a text prompt to the Deepseek API and returns the generated completion.
    
    The endpoint accepts:
    - A required text prompt
    - Optional max_tokens parameter to limit response length
    - Optional temperature parameter to control response randomness
    
    Returns the AI-generated completion text.
    """,
    response_description="The AI-generated text completion",
    tags=["Completion"],
    status_code=200,
    responses={
        200: {
            "description": "Successful completion generation",
            "content": {
                "application/json": {
                    "example": {
                        "completion": "Here's a Python function to calculate Fibonacci numbers:\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error or API key not configured",
            "content": {
                "application/json": {
                    "example": {"detail": "API key not configured"}
                }
            }
        },
        504: {
            "description": "Gateway timeout - Deepseek API took too long to respond",
            "content": {
                "application/json": {
                    "example": {"detail": "Request timeout"}
                }
            }
        }
    }
)
async def get_completion(request: PromptRequest):
    logger.info(f"Received completion request with prompt: {request.prompt[:100]}...")
    
    if not DEEPSEEK_API_KEY:
        logger.error("API key not configured")
        raise HTTPException(
            status_code=500,
            detail="API key not configured. Please set DEEPSEEK_API_KEY environment variable."
        )
    
    try:
        # Initialize the client inside the function
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": request.prompt}
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False
        )
        
        completion_text = response.choices[0].message.content
        logger.info(f"Response: {completion_text}")
        
        return CompletionResponse(completion=completion_text)
            
    except Exception as e:
        logger.exception(f"Unexpected error during API request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Search API service")
    logger.info(f"API Version: {app.version}")
    logger.info(f"Environment: {os.getenv('ENV', 'development')}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Search API service")

if __name__ == "__main__":
    import uvicorn # type: ignore
    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
