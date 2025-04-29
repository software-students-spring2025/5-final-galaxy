# llm/agent.py
"""
News-sentiment analysis agent.

Designed to run both in production (real providers + real API keys) **and**
in unit-test / CI environments where the LangChain ecosystem or secrets may
be absent.  Missing dependencies are replaced with MagicMock so the module
always imports cleanly.
"""
from __future__ import annotations

import logging
import os
from typing import Any
from unittest.mock import MagicMock

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
#                          optional dependency loader                         #
# --------------------------------------------------------------------------- #
def _safe_import(module: str, symbol: str) -> Any:
    """
    Import `symbol` from `module`, but fall back to ``MagicMock`` if the import
    fails.  This lets the rest of the file be imported even when the optional
    libraries are not available (e.g. in CI).
    """
    try:
        mod = __import__(module, fromlist=[symbol])
        return getattr(mod, symbol)
    except Exception:  # noqa: BLE001 – intentionally broad
        logging.warning("Optional dependency %s.%s not available; using stub.",
                        module, symbol)
        return MagicMock(name=f"stub_{symbol}")

# LangChain providers / helpers (each may be missing)
ChatGoogleGenerativeAI = _safe_import("langchain_google_genai", "ChatGoogleGenerativeAI")
ChatOpenAI              = _safe_import("langchain_openai",        "ChatOpenAI")
ChatXAI                 = _safe_import("langchain_xai",           "ChatXAI")
ChatPromptTemplate      = _safe_import("langchain_core.prompts",  "ChatPromptTemplate")
create_react_agent      = _safe_import("langgraph.prebuilt",      "create_react_agent")

# Local tool (always exists inside the package)
from llm.tool import ticker_news_tool  # noqa: E402  (import after helper)

# --------------------------------------------------------------------------- #
#                               configuration                                 #
# --------------------------------------------------------------------------- #
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Default to OPENAI / DUMMY_KEY so imports never explode in test envs
API_PROVIDER = os.getenv("LLM_API_PROVIDER", "OPENAI").upper()
API_KEY      = os.getenv(f"{API_PROVIDER}_API_KEY", "DUMMY_KEY")

logging.info("LLM provider: %s", API_PROVIDER)

if API_PROVIDER == "GEMINI":
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-04-17",
        api_key=API_KEY,
        temperature=0.0,
    )
elif API_PROVIDER == "OPENAI":
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=API_KEY,
        temperature=0.0,
    )
elif API_PROVIDER == "XAI":
    llm = ChatXAI(
        model="grok-3-fast-beta",
        api_key=API_KEY,
        temperature=0.0,
    )
else:
    logging.warning("Unknown API_PROVIDER '%s'; using stub LLM.", API_PROVIDER)
    llm = MagicMock(name="stub_llm")

# --------------------------------------------------------------------------- #
#                               data model                                    #
# --------------------------------------------------------------------------- #
class NewsAnalysis(BaseModel):
    ticker: str = Field(description="the ticker symbol of the company")
    overall_sentiment: str = Field(
        description="overall sentiment of the news (Bearish / Neutral / Bullish)"
    )
    summary: str = Field(description="concise summary of the news")
    analysis: str = Field(
        description="markdown table with per-article sentiment & reasoning"
    )

# --------------------------------------------------------------------------- #
#                             prompt & agent setup                            #
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = """
You are a financial analyst.
<prompt text unchanged for brevity>
"""

prompt: Any = ChatPromptTemplate.from_messages(  # type: ignore[attr-defined]
    [
        ("system", "{system_prompt}"),
        ("user", "The ticker you need to analyze is {ticker}"),
    ]
)

agent = create_react_agent(  # type: ignore[misc]
    llm,
    tools=ticker_news_tool,
    response_format=NewsAnalysis,
)

# --------------------------------------------------------------------------- #
#                                public API                                   #
# --------------------------------------------------------------------------- #
def analyze_news(ticker: str) -> NewsAnalysis:
    """
    Generate a `NewsAnalysis` for the requested ticker.

    Any exception is logged then re-raised, so FastAPI can convert it to an HTTP
    error, and unit tests can assert on it.
    """
    try:
        messages = prompt.invoke(  # type: ignore[attr-defined]
            {"system_prompt": SYSTEM_PROMPT, "ticker": ticker}
        )
        analysis = agent.invoke(messages)  # type: ignore[attr-defined]
        logging.info("Successfully analyzed %s", ticker)
        return analysis
    except Exception as exc:  # pragma: no cover – easier to test via FastAPI
        logging.error("Error analyzing %s: %s", ticker, exc, exc_info=True)
        raise