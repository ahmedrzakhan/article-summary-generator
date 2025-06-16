import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
from config import settings
from backend.models import SummaryRequest, SummaryResponse, ErrorResponse
from services.gemini_service import gemini_service
from services.langsmith_service import langsmith_service

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Article Summary Generator API")
    yield
    logger.info("Shutting down Article Summary Generator API")

app = FastAPI(
    title="Article Summary Generator API",
    description="An intelligent article summarization service using Google's Gemini API",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit default ports
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=get_remote_address(request)
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=round(process_time, 4)
    )
    
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        error=str(exc),
        method=request.method,
        url=str(request.url),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail="An unexpected error occurred. Please try again later.",
            error_code="INTERNAL_ERROR"
        ).dict()
    )

@app.get("/")
async def root():
    return {
        "message": "Article Summary Generator API",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "gemini": "configured" if settings.gemini_api_key else "not_configured",
            "langsmith": "enabled" if langsmith_service.enabled else "disabled"
        }
    }

@app.post("/summarize", response_model=SummaryResponse)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}second")
async def summarize_article(
    request: Request,
    summary_request: SummaryRequest
):
    try:
        logger.info(
            "Summarization request received",
            text_length=len(summary_request.text),
            summary_length=summary_request.summary_length,
            client_ip=get_remote_address(request)
        )
        
        # Generate summary using Gemini
        result = await gemini_service.summarize_text(
            text=summary_request.text,
            summary_length=summary_request.summary_length
        )
        
        # Track with LangSmith
        result = await langsmith_service.track_summarization(
            text=summary_request.text,
            summary_length=summary_request.summary_length,
            result=result
        )
        
        response = SummaryResponse(**result)
        
        logger.info(
            "Summarization completed successfully",
            compression_ratio=response.compression_ratio,
            processing_time=response.processing_time
        )
        
        return response
        
    except ValueError as e:
        logger.warning("Validation error", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Validation error",
                detail=str(e),
                error_code="VALIDATION_ERROR"
            ).dict()
        )
    
    except Exception as e:
        logger.error("Summarization failed", error=str(e), exc_info=True)
        
        # Log error to LangSmith
        langsmith_service.log_error(e, {
            "text_length": len(summary_request.text),
            "summary_length": summary_request.summary_length
        })
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Summarization failed",
                detail="Unable to generate summary. Please try again.",
                error_code="SUMMARIZATION_ERROR"
            ).dict()
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )