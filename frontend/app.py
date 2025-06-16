import streamlit as st
import httpx
import asyncio
import time
import json
from typing import Optional, Dict, Any
import validators

# Configure page
st.set_page_config(
    page_title="Article Summary Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }

    .stats-container {
        display: flex;
        justify-content: space-around;
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }

    .stat-box {
        text-align: center;
        padding: 0.5rem;
    }

    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }

    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }

    .summary-box {
        background: #ffffff !important;
        color: #1a1a1a !important;
        padding: 1.5rem !important;
        border-radius: 10px !important;
        border: 2px solid #667eea !important;
        margin: 1rem 0 !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
        box-shadow: 0 4px 6px rgba(102, 126, 234, 0.1) !important;
    }

     .summary-box p {
        color: #1a1a1a !important;
        margin: 0 !important;
        font-weight: 400 !important;
    }

    .error-box {
        background: #ffe6e6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ff4444;
        color: #cc0000;
        margin: 1rem 0;
    }

    .success-box {
        background: #e6ffe6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #44ff44;
        color: #008800;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'summary_history' not in st.session_state:
    st.session_state.summary_history = []

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = 30.0

    async def summarize_text(self, text: str, summary_length: str = "medium") -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/summarize",
                json={
                    "text": text,
                    "summary_length": summary_length
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json()
                raise Exception(f"API Error: {error_data.get('detail', {}).get('error', 'Unknown error')}")

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.json() if response.status_code == 200 else None
        except:
            return None

def validate_input(text: str) -> Optional[str]:
    if not text.strip():
        return "Please enter some text to summarize."

    if len(text.strip()) < 50:
        return "Text must be at least 50 characters long."

    if len(text) > 50000:
        return "Text is too long. Please limit to 50,000 characters."

    words = text.split()
    if len(words) < 10:
        return "Text must contain at least 10 words."

    return None

def display_stats(text: str, summary: Optional[str] = None, processing_time: Optional[float] = None):
    words = len(text.split())
    chars = len(text)

    cols = st.columns(4)

    with cols[0]:
        st.metric("Characters", f"{chars:,}")

    with cols[1]:
        st.metric("Words", f"{words:,}")

    if summary:
        summary_words = len(summary.split())
        compression_ratio = (summary_words / words) * 100 if words > 0 else 0

        with cols[2]:
            st.metric("Compression", f"{compression_ratio:.1f}%")

    if processing_time:
        with cols[3]:
            st.metric("Processing Time", f"{processing_time:.2f}s")

async def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📝 Article Summary Generator</h1>
        <p>Transform lengthy articles into concise, intelligent summaries using AI</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize API client
    api_client = APIClient()

    # Check API health
    with st.spinner("Checking service status..."):
        health = await api_client.health_check()

    if health:
        if health.get('services', {}).get('gemini') == 'configured':
            st.success("✅ Service is running and ready!")
        else:
            st.warning("⚠️ Service is running but Gemini API is not configured.")
    else:
        st.error("❌ Unable to connect to the summarization service. Please ensure the backend is running.")
        st.info("Run `python -m backend.main` to start the backend service.")
        return

    # Main interface
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📄 Enter Your Article")

        # Text input
        text_input = st.text_area(
            "Paste your article or text here:",
            height=300,
            placeholder="Paste your article, blog post, research paper, or any text you'd like to summarize here...",
            help="Enter at least 50 characters and 10 words for the best results."
        )

        # Input validation and stats
        if text_input:
            validation_error = validate_input(text_input)
            if validation_error:
                st.error(validation_error)
            else:
                display_stats(text_input)

        # Summary length selection
        summary_length = st.selectbox(
            "Summary Length:",
            options=["short", "medium", "long"],
            index=1,
            help="Short: 2-3 sentences, Medium: 1-2 paragraphs, Long: 2-3 paragraphs"
        )

        # Action buttons
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

        with col_btn1:
            summarize_btn = st.button("🚀 Generate Summary", type="primary", use_container_width=True)

        with col_btn2:
            clear_btn = st.button("🗑️ Clear", use_container_width=True)

        if clear_btn:
            st.rerun()

    with col2:
        st.subheader("📊 Quick Stats")

        if text_input:
            words = len(text_input.split())
            chars = len(text_input)

            st.metric("Total Characters", f"{chars:,}")
            st.metric("Total Words", f"{words:,}")
            st.metric("Estimated Reading Time", f"{max(1, words // 200)} min")

        # Recent summaries
        if st.session_state.summary_history:
            st.subheader("📝 Recent Summaries")
            for i, summary_data in enumerate(reversed(st.session_state.summary_history[-3:])):
                with st.expander(f"Summary {len(st.session_state.summary_history) - i}"):
                    st.write(summary_data['summary'][:100] + "...")
                    st.caption(f"Processed: {summary_data['timestamp']}")

    # Process summarization
    if summarize_btn and text_input:
        validation_error = validate_input(text_input)
        if validation_error:
            st.error(validation_error)
        else:
            with st.spinner("🤖 Generating your summary... This may take a few moments."):
                try:
                    start_time = time.time()
                    result = await api_client.summarize_text(text_input, summary_length)
                    end_time = time.time()

                    # Display results
                    st.success("✅ Summary generated successfully!")

                    # Summary display
                    st.subheader("📋 Generated Summary")
                    st.markdown(f"""
                    <div class="summary-box">
                        <p>{result['summary']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Detailed stats
                    st.subheader("📈 Summary Statistics")
                    display_stats(
                        text_input,
                        result['summary'],
                        result.get('processing_time', end_time - start_time)
                    )

                    # Additional metrics
                    col_m1, col_m2, col_m3 = st.columns(3)

                    with col_m1:
                        st.metric(
                            "Original Length",
                            f"{result['original_length']} words"
                        )

                    with col_m2:
                        st.metric(
                            "Summary Length",
                            f"{result['summary_length']} words"
                        )

                    with col_m3:
                        st.metric(
                            "Compression Ratio",
                            f"{result['compression_ratio']:.1%}"
                        )

                    # Save to history
                    st.session_state.summary_history.append({
                        'original_text': text_input[:200] + "..." if len(text_input) > 200 else text_input,
                        'summary': result['summary'],
                        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'stats': result
                    })

                    # Download option
                    summary_text = f"""
Article Summary
Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}
Summary Length: {summary_length}

Original Text ({result['original_length']} words):
{text_input}

Summary ({result['summary_length']} words):
{result['summary']}

Statistics:
- Compression Ratio: {result['compression_ratio']:.1%}
- Processing Time: {result['processing_time']:.2f} seconds
"""

                    st.download_button(
                        label="📥 Download Summary",
                        data=summary_text,
                        file_name=f"summary_{int(time.time())}.txt",
                        mime="text/plain"
                    )

                except Exception as e:
                    st.error(f"❌ Error generating summary: {str(e)}")
                    st.info("Please try again with different text or check your internet connection.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🤖 Powered by Google Gemini AI | Built with Streamlit & FastAPI</p>
    <p>For best results, provide well-structured text with clear paragraphs and sentences.</p>
</div>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    asyncio.run(main())