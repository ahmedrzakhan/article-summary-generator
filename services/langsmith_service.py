import os
from typing import Optional, Dict, Any
from langsmith import Client, traceable
import structlog
from config import settings

logger = structlog.get_logger()


class LangSmithService:
    def __init__(self):
        print("🔍 LANGSMITH DEBUG:")
        print(f"  LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
        print(f"  LANGCHAIN_API_KEY: {os.getenv('LANGCHAIN_API_KEY', 'NOT SET')[:10]}...")  # Only show first 10 chars
        print(f"  LANGCHAIN_ENDPOINT: {os.getenv('LANGCHAIN_ENDPOINT')}")
        print(f"  LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")

        import langsmith
        print(f"🔍 LANGSMITH SDK Version: {langsmith.__version__}")

# Force set the environment variable as string
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_TRACING"] = "true"

        print(f"🔍 LANGSMITH: After forcing env vars - LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
        print(f"🔍 LANGSMITH: After forcing env vars - LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")

        self.client: Optional[Client] = None
        self.enabled = False

        if settings.langchain_tracing_v2 and settings.langchain_api_key:
            try:
                # Set up LangSmith environment variables
                os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2)
                os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
                os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
                os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

                self.client = Client(
                    api_url=settings.langchain_endpoint,
                    api_key=settings.langchain_api_key
                )

                # Test connection
                self.client.list_runs(limit=1)
                self.enabled = True
                logger.info("LangSmith integration enabled", project=settings.langchain_project)

            except Exception as e:
                logger.warning("Failed to initialize LangSmith", error=str(e))
                self.enabled = False
        else:
            logger.info("LangSmith integration disabled - missing configuration")

    @traceable(run_type="chain", name="article_summary_pipeline")
    async def track_summarization(
        self,
        text: str,
        summary_length: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        print(f"🔍 LANGSMITH: track_summarization called!")
        print(f"🔍 LANGSMITH: @traceable decorator should be active")
        print(f"🔍 LANGSMITH: Environment check - LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")

        if not self.enabled:
            return result

        try:
            # Add metadata for tracking
            metadata = {
                "input_length": len(text),
                "input_word_count": len(text.split()),
                "summary_length_setting": summary_length,
                "output_word_count": result.get("summary_length", 0),
                "compression_ratio": result.get("compression_ratio", 0),
                "processing_time": result.get("processing_time", 0),
                "model": "gemini-pro"
            }

            # Log metrics for analysis
            if self.client:
                await self._log_metrics(metadata)

            logger.info("Summarization tracked in LangSmith", metadata=metadata)

        except Exception as e:
            logger.warning("Failed to track in LangSmith", error=str(e))

        return result

    async def _log_metrics(self, metadata: Dict[str, Any]):
        try:
            # You can extend this to create custom datasets or feedback
            # This is a placeholder for additional LangSmith features
            pass
        except Exception as e:
            logger.warning("Failed to log metrics to LangSmith", error=str(e))

    def log_error(self, error: Exception, context: Dict[str, Any]):
        if not self.enabled:
            return

        try:
            logger.error(
                "Error in summarization pipeline",
                error=str(error),
                context=context,
                langsmith_project=settings.langchain_project
            )
        except Exception as e:
            logger.warning("Failed to log error to LangSmith", error=str(e))


# Singleton instance
langsmith_service = LangSmithService()