import asyncio
import time
from typing import Optional, Dict, Any
import google.generativeai as genai
from langsmith import traceable
import structlog
from config import settings

logger = structlog.get_logger()


class GeminiService:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Configure safety settings
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]

    def _get_summary_prompt(self, text: str, length: str) -> str:
        length_instructions = {
            "short": "in 2-3 sentences (50-100 words)",
            "medium": "in 1-2 paragraphs (100-200 words)",
            "long": "in 2-3 paragraphs (200-300 words)"
        }

        instruction = length_instructions.get(length, length_instructions["medium"])

        return f"""
        Please provide a comprehensive summary of the following text {instruction}.

        Focus on:
        1. Main topics and key points
        2. Important facts and findings
        3. Conclusions or recommendations if present
        4. Keep the summary coherent and well-structured

        Text to summarize:
        {text}

        Summary:
        """

    @traceable(run_type="llm", name="gemini_summarize")
    async def summarize_text(
        self,
        text: str,
        summary_length: str = "medium",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                prompt = self._get_summary_prompt(text, summary_length)
                print(f"🔄 GEMINI SERVICE: Attempt {attempt + 1}, calling AI...")

                logger.info(
                    "Generating summary",
                    attempt=attempt + 1,
                    text_length=len(text),
                    summary_length=summary_length
                )

                # Run the synchronous generation in a thread pool
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    self._generate_with_retry,
                    prompt
                )

                print(f"✅ GEMINI SERVICE: AI call successful, response length: {len(response.text) if response and response.text else 'None'}")

                if not response or not response.text:
                    raise ValueError("Empty response from Gemini API")

                summary = response.text.strip()
                processing_time = time.time() - start_time

                # Calculate metrics
                original_length = len(text.split())
                summary_word_count = len(summary.split())
                compression_ratio = summary_word_count / original_length if original_length > 0 else 0


                logger.info(
                    "Summary generated successfully",
                    processing_time=processing_time,
                    original_words=original_length,
                    summary_words=summary_word_count,
                    compression_ratio=compression_ratio
                )

                return {
                    "summary": summary,
                    "original_length": original_length,
                    "summary_length": summary_word_count,
                    "compression_ratio": compression_ratio,
                    "processing_time": processing_time
                }

            except Exception as e:
                logger.warning(
                    "Summary generation attempt failed",
                    attempt=attempt + 1,
                    error=str(e),
                    max_retries=max_retries
                )

                if attempt == max_retries - 1:
                    logger.error("All summary generation attempts failed", error=str(e))
                    raise

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Failed to generate summary after all retries")

    def _generate_with_retry(self, prompt: str):
        try:
            return self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config={
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
            )
        except Exception as e:
            logger.error("Gemini API call failed", error=str(e))
            raise


# Singleton instance
gemini_service = GeminiService()