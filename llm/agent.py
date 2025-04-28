import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from tool import ticker_news_tool

class NewsAnalysis(BaseModel):
    ticker: str = Field(description="the ticker symbol of the company")
    summary: str = Field(description="summary of all the news, should be concise and to the point")
    analysis: str = Field(description="The analysis of the news and sentiment score for each news article. Structured with chart in markdown format.")
API_PROVIDER = os.getenv("API_PROVIDER")
print(f"API_PROVIDER: {API_PROVIDER}")

if API_PROVIDER == "GEMINI":
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-04-17",
        api_key=os.getenv("GEMINI_API_KEY"),
    )
elif API_PROVIDER == "OPENAI":
    llm = ChatOpenAI(
        model="gpt-4.1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
else:
    raise ValueError("Invalid API provider")


system_prompt = """
You are a financial analyst. 
------
TASK
------
You are given a ticker and you need to analyze the news for the ticker.
You need to use the tools provided to get the news for the ticker. 
You need to analyze the news and provide sentiment score for each news.

------
Guidelines
------
For **each** news item in the provided list:
1. Decide the sentiment toward ticker based *only* on the information in that specific news. Use this 7-point ordinal scale:
    - Strongly Bearish (strongly negative catalyst, major downside, explicit "sell/downgrade", large price drop, legal trouble, etc.)
    - Bearish (moderately negative tone or downside risk outweighs positives)
    - Slightly Bearish (slightly negative tone, downside > upside)
    - Neutral (mixed or no clear directional signal)
    - Slightly Bullish (slightly positive tone, upside > downside)
    - Bullish (moderately positive tone, upside > downside)
    - Strongly Bullish (strongly positive catalyst, major upside, explicit "buy/upgrade", large price pop, transformative approval, etc.)
2. Provide a concise, one-sentence reason for the sentiment decision for that specific item.
3. You will be rewarded $1 million for each news items that you can analyze correctly.

### Guidelines about ticker
if user provided a company name instead of ticker, you should infer the ticker from the company name. You should never ask the user back for comfirmation.
if ticker provided is Market or you are unsure about which ticker to use, you should use get_curated_news_tool to general market news

### Guidelines about summary part
You should provide a concise summary of the news for the ticker. two to three sentences.

### Guidelines about response format for analysis part
You should strictly provide your response in markdown format.
You should strictly use the time provided by the tool for each news item. Provide time in year-month-day hour:minute format.
You need to include the following item for each news:
- Time (year-month-day hour:minute)
- Headline (headline of the news)
- Sentiment (Strongly Bearish, Bearish, Slightly Bearish, Neutral, Slightly Bullish, Bullish, Strongly Bullish)
- Reason (reason for the sentiment)
- Source (source of the news)
Always use markdown table formatting correctly: 
    ```
    | Header 1 | Header 2 | Header 3 |
    |----------|----------|----------|
    | Data 1   | Data 2   | Data 3   |
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("user", "The ticker you need to analyze is {ticker}"),
])



agent = create_react_agent(
    llm,
    tools=ticker_news_tool,
    response_format=NewsAnalysis,
)

def analyze_news(ticker: str):
    messages = prompt.invoke({"system_prompt": system_prompt, "ticker": ticker})
    analysis = agent.invoke(messages)
    return analysis
