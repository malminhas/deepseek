"""
Deepseek Backend API Service
---------------------------

A FastAPI backend service that integrates with the Deepseek API for text completions.

This service provides a single endpoint that accepts text prompts and returns
AI-generated completions using the Deepseek language model.

Version History:
    1.1.0 - (Latest Release) - 26.01.25
        - Added Gumtree hosted Deepseek API integration
        - Added Perplexity API integration
        - Added Ollama API integration
    1.0.0 - 26.01.25
        - Added Deepseek API integration

Installation:
    pip install fastapi uvicorn httpx pydantic openai groq ollama

Environment Variables:
    DEEPSEEK_API_KEY: Your Deepseek API key (required)
    GROQ_API_KEY: Your Groq API key (required)
    PERPLEXITY_API_KEY: Your Perplexity API key (required)

Google Cloud Setup:
    1. Install Google Cloud SDK



Running the service:
    Development with hot reload:
        uvicorn search-backend:app --reload --host 0.0.0.0 --port 8001
    
    Production:
        uvicorn search-backend:app --host 0.0.0.0 --port 8001

Dependencies:
    - FastAPI
    - uvicorn (for serving)
    - pydantic (for data validation)
    - httpx (for HTTP requests)
    - openai (for OpenAI API integration)
    - groq (for Groq API integration)
    - ollama (for Ollama API integration)

Documentation:
    Swagger UI: http://localhost:8001/docs
    ReDoc: http://localhost:8001/redoc

Endpoints:
    POST /completion: Generate text completion from a prompt

License: MIT
"""

from fastapi import FastAPI, HTTPException # type: ignore
from pydantic import BaseModel, Field, validator # type: ignore
from openai import OpenAI # type: ignore
from groq import Groq  # type: ignore
import os
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware # type: ignore
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from enum import Enum
import openai # type: ignore
import httpx  # type: ignore
import json
import fastapi # type: ignore
from openai import AsyncOpenAI, APIError, APITimeoutError # type: ignore
from fastapi.responses import StreamingResponse, Response  # type: ignore

VERSION = "1.1.0"
AUTHOR = "Mal Minhas"
RELEASE_DATE = "31.01.2025"
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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
GUMTREE_API_URL = os.getenv("GUMTREE_API_URL")
TIMEOUT = 30.0  # Timeout in seconds for all API calls
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

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

# Model configuration
class ModelName(str, Enum):
    CHAT = "deepseek-chat"
    REASONER = "deepseek-reasoner"
    GROQ = "groq-deepseek-r1"
    PERPLEXITY = "perplexity-sonar"
    OLLAMA = "ollama-deepseek-r1"
    GUMTREE = "gumtree-deepseek-r1"  # Gumtree model

class ModelConfig(BaseModel):
    model: ModelName = Field(
        default=ModelName.CHAT,
        description="The AI model to use for completions"
    )

# Global model configuration
current_model = {"model": ModelName.CHAT}

# Model endpoints
@app.get(
    "/model",
    response_model=ModelConfig,
    summary="Get current model",
    description="Returns the currently selected AI model",
    tags=["Model Configuration"]
)
async def get_model():
    logger.info(f"Getting current model: {current_model['model']}")
    return current_model

@app.put(
    "/model",
    response_model=ModelConfig,
    summary="Set current model",
    description="Updates the AI model to use for completions",
    tags=["Model Configuration"]
)
async def set_model(config: ModelConfig):
    logger.info(f"Setting model to: {config.model}")
    global current_model
    current_model = {"model": config.model}
    return current_model

# Completion endpoint models
class PromptRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="The text prompt to send to the Deepseek API",
        example="Write a function that calculates fibonacci numbers",
        min_length=1
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
        description="Controls randomness in the response",
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
        example="Here's a Python function to calculate Fibonacci numbers..."
    )

async def handle_deepseek_completion(request: PromptRequest) -> StreamingResponse:
    """Handle completion requests for Deepseek models"""
    if not DEEPSEEK_API_KEY:
        logger.error("Deepseek API key not configured")
        raise HTTPException(
            status_code=500,
            detail="DEEPSEEK_API_KEY environment variable must be set"
        )
    
    try:
        client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
            timeout=TIMEOUT,
            max_retries=0
        )
        
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Format your responses using markdown."
                },
                {"role": "user", "content": request.prompt}
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True
        )

        async def stream_response():
            try:
                buffer = ""
                async for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        buffer += chunk.choices[0].delta.content
                        # Send buffer when we hit a natural break point or accumulated enough characters
                        if any(c in buffer for c in ["\n", ".", "!", "?"]) or len(buffer) > 80:
                            yield buffer
                            buffer = ""
                # Send any remaining content in the buffer
                if buffer:
                    yield buffer
            except Exception as e:
                logger.exception("Error during streaming")
                raise HTTPException(status_code=500, detail=str(e))

        return StreamingResponse(
            stream_response(),
            media_type="text/plain",
        )

    except APITimeoutError as e:
        logger.exception("OpenAI API timeout")
        raise HTTPException(status_code=408, detail="Request timed out")
    except APIError as e:
        logger.exception("OpenAI API error")
        raise HTTPException(status_code=getattr(e, 'status_code', 500), detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during completion request")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_groq_completion(request: PromptRequest) -> str:
    """Handle completion requests for Groq model"""
    if not GROQ_API_KEY:
        logger.error("Groq API key not configured")
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY environment variable must be set"
        )
    
    try:
        client = Groq(
            api_key=GROQ_API_KEY,
            timeout=TIMEOUT,
            max_retries=0
        )
        
        # Add markdown formatting instruction to system prompt
        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful assistant. Format your responses using markdown. "
                              "When providing Python code examples, use proper 4-space indentation and "
                              "format with ```python language identifier. Ensure proper line breaks between sections."
                },
                {"role": "user", "content": request.prompt}
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False
        )
        
        completion_text = response.choices[0].message.content
        
        # Split into sections based on double newlines
        sections = completion_text.split('\n\n')
        formatted_sections = []
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Handle Python code blocks
            if section.startswith('```python'):
                lines = section.split('\n')
                formatted_lines = []
                in_code = False
                base_indent = 0
                
                for line in lines:
                    if line.startswith('```python'):
                        formatted_lines.append(line)
                        in_code = True
                    elif line.startswith('```'):
                        formatted_lines.append(line)
                        in_code = False
                    elif in_code:
                        # Count leading spaces to determine indent level
                        stripped = line.lstrip()
                        if stripped:  # Non-empty line
                            indent_level = (len(line) - len(stripped)) // 4
                            formatted_lines.append('    ' * indent_level + stripped)
                    else:
                        formatted_lines.append(line)
                
                section = '\n'.join(formatted_lines)
                formatted_sections.append(section)
                continue
                
            # Handle other sections as before
            if section.replace('.', '').strip().startswith('1'):
                lines = section.split('\n')
                formatted_lines = []
                for line in lines:
                    line = line.strip()
                    if line:
                        if line[0].isdigit():
                            formatted_lines.append(f"{line}")
                        else:
                            formatted_lines.append(f"   {line}")
                section = '\n'.join(formatted_lines)
            
            formatted_sections.append(section)
        
        # Join sections with proper markdown spacing
        markdown_text = '\n\n'.join(formatted_sections)
        
        # Add a header if none exists
        if not any(line.strip().startswith('#') for line in markdown_text.split('\n')):
            markdown_text = f"### Response\n\n{markdown_text}"
        
        return markdown_text
        
    except openai.APITimeoutError as e:
        error_msg = (
            f"Request to Groq API timed out after {TIMEOUT} seconds. "
            f"Model: deepseek-r1-distill-llama-70b, "
            f"Prompt length: {len(request.prompt)} chars"
        )
        logger.warning(error_msg)
        raise HTTPException(
            status_code=504,
            detail=error_msg
        )
    except Exception as e:
        logger.exception(f"Groq API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")

async def handle_perplexity_completion(request: PromptRequest) -> StreamingResponse:
    """Handle completion requests for Perplexity Sonar model"""
    try:
        client = AsyncOpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai",
            timeout=TIMEOUT,
            max_retries=0
        )
        
        response = await client.chat.completions.create(
            model="sonar-reasoning",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful assistant. Format your responses using markdown. "
                              "Use numbered references in square brackets [1], [2], etc. in your text. "
                              #"List all references at the end of your response as hyperlinks with descriptive titles."
                },
                {"role": "user", "content": request.prompt}
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True
        )

        async def stream_response():
            try:
                buffer = ""
                citations = []
                
                async for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        buffer += chunk.choices[0].delta.content
                        if any(c in buffer for c in ["\n", ".", "!", "?"]) or len(buffer) > 80:
                            yield buffer
                            buffer = ""
                            
                    if hasattr(chunk, 'citations') and chunk.citations:
                        citations = chunk.citations
                
                if buffer:
                    yield buffer
                

                # Add references with hyperlinks
                if citations:
                    yield "\n\n## Citations:\n\n"
                    for i, url in enumerate(citations, 1):
                        # Each citation on its own line with consistent indentation
                        yield f"[{i}] [{url}]({url})\n\n"  # Added extra newline for list spacing

                
            except Exception as e:
                logger.exception("Error during streaming")
                raise HTTPException(status_code=500, detail=str(e))

        return StreamingResponse(
            stream_response(),
            media_type="text/plain",
        )

    except APITimeoutError as e:
        logger.exception("OpenAI API timeout")
        raise HTTPException(status_code=408, detail="Request timed out")
    except APIError as e:
        logger.exception("OpenAI API error")
        raise HTTPException(status_code=getattr(e, 'status_code', 500), detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during completion request")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_ollama_completion(request: PromptRequest) -> fastapi.responses.StreamingResponse:
    """Handle completion requests for Ollama instance with streaming support."""
    
    model = "deepseek-r1"
    logger.info("Attempting request to Ollama API")
    
    async def generate():
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_HOST}/api/generate",
                    json={
                        "model": model,
                        "prompt": request.prompt,
                        "stream": True,
                        "options": {
                            "num_predict": request.max_tokens,
                            "temperature": request.temperature
                        }
                    },
                    timeout=TIMEOUT
                ) as response:
                    if response.status_code != 200:
                        error_msg = f"Ollama API request failed with status {response.status_code}"
                        logger.error(error_msg)
                        yield f"Error: {error_msg}"
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if 'response' in data:
                                yield data['response']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse Ollama response: {e}")
                            continue

        except httpx.TimeoutException:
            error_msg = f"Request to Ollama API timed out after {TIMEOUT} seconds"
            logger.error(error_msg)
            yield f"Error: {error_msg}"
            
        except Exception as e:
            error_msg = f"Unexpected error connecting to Ollama API: {str(e)}"
            logger.exception(error_msg)
            yield f"Error: {error_msg}"

    return fastapi.responses.StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

async def handle_gumtree_completion(request: PromptRequest) -> StreamingResponse:
    """Handle completion requests for Gumtree's DeepSeek instance with streaming support."""
    
    if not GUMTREE_API_URL:
        logger.error("Gumtree API URL not configured")
        raise HTTPException(status_code=500, detail="Gumtree API URL not configured")

    async def generate():
        try:
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
            
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    GUMTREE_API_URL,
                    json={
                        "model": "deepseek-r1-8b",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a helpful assistant. Format your responses using markdown.",
                                "name": "system"
                            },
                            {
                                "role": "user",
                                "content": request.prompt,
                                "name": "user"
                            }
                        ],
                        "temperature": request.temperature,
                        "max_tokens": request.max_tokens,
                        "stream": True
                    },
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        error_msg = f"Request failed with status {response.status_code}: {response.text}"
                        logger.error(error_msg)
                        yield error_msg
                        return

                    buffer = ""
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # Skip "data: " prefix
                                if 'choices' in data and data['choices']:
                                    content = data['choices'][0].get('delta', {}).get('content', '')
                                    if content:
                                        yield content
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON: {e}")
                                continue

        except Exception as e:
            error_msg = f"Error connecting to Gumtree API: {str(e)}"
            logger.error(error_msg)
            yield error_msg

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.post("/completion")
async def get_completion(request: PromptRequest) -> fastapi.Response:
    """Get a completion from the selected model."""
    logger.info(f"Received completion request: {request}")
    
    try:
        # All these models now return StreamingResponse apart from Groq
        if current_model["model"] == ModelName.CHAT or current_model["model"] == ModelName.REASONER:
            return await handle_deepseek_completion(request)
        elif current_model["model"] == ModelName.GROQ:
            completion_text = await handle_groq_completion(request)
        elif current_model["model"] == ModelName.PERPLEXITY:
            return await handle_perplexity_completion(request)
        elif current_model["model"] == ModelName.OLLAMA:
            return await handle_ollama_completion(request)
        elif current_model["model"] == ModelName.GUMTREE:
            return await handle_gumtree_completion(request)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown model: {current_model['model']}"
            )
        
        # Return non-streaming responses for models that don't stream yet
        return fastapi.Response(
            content=completion_text,
            media_type="text/plain"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during completion request")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

class VersionInfo(BaseModel):
    version: str = Field(..., description="API version number")
    author: str = Field(..., description="Author of the API")
    releaseDate: str = Field(..., description="Release date of current version")
    license: str = Field(..., description="License type")
    environment: str = Field(..., description="Current running environment")

@app.get(
    "/version",
    response_model=VersionInfo,
    summary="Get API version information",
    description="Returns the current version, author, release date and license information",
    tags=["System Information"]
)
async def get_version():
    """Get the API version information."""
    logger.info("Version information requested")
    return {
        "version": VERSION,
        "author": AUTHOR,
        "releaseDate": RELEASE_DATE,
        "license": LICENSE,
        "environment": os.getenv('ENV', 'development')
    }

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
    uvicorn.run(app, host="0.0.0.0", port=8083)
