# Stock Analysis Dashboard

[![Web App CI/CD](https://github.com/software-students-spring2025/5-final-galaxy/actions/workflows/web-app.yml/badge.svg)](https://github.com/software-students-spring2025/5-final-galaxy/actions/workflows/web-app.yml)
[![LLM Service CI/CD](https://github.com/software-students-spring2025/5-final-galaxy/actions/workflows/llm.yml/badge.svg)](https://github.com/software-students-spring2025/5-final-galaxy/actions/workflows/llm.yml)

## Description

In this project, we build a stock analysis dashboard. Key features include:

1.  **LLM-Powered Sentiment Analysis:** Enter any stock symbol to retrieve recent news articles associated with it. Our integrated Large Language Model (LLM) analyzes these articles to provide insightful sentiment analysis, offering a deeper understanding beyond raw numbers.
2.  **TradingView Integration:** We've embedded interactive widgets from TradingView to display real-time stock prices and general market information for the queried symbols, keeping you informed on current performance.

## Docker Hub Images

-   **Web App:** [Link to Web App Docker Hub Image](https://hub.docker.com/r/YOUR_DOCKERHUB_USERNAME/YOUR_WEB_APP_IMAGE)
-   **LLM Service:** [Link to LLM Service Docker Hub Image](https://hub.docker.com/r/YOUR_DOCKERHUB_USERNAME/YOUR_LLM_SERVICE_IMAGE)
<!-- TODO: Replace YOUR_DOCKERHUB_USERNAME and image names with your actual Docker Hub details -->

## Team Members

-   [Alan Chen](https://github.com/Chen-zexi)
-   [Jackson Chen](https://github.com/jaxxjj)
-   [Ray Huang](https://github.com/RayHuang3339)
-   [Ethan Yu](https://github.com/ethanyuu910)

## Project Structure

```
├── common/                  # Shared code between subsystems
│   └── models.py            # Database models 
├── llm/                     # LLM service for sentiment analysis
│   ├── Dockerfile           # Container configuration
│   ├── requirements.txt     # Python dependencies
│   ├── agent.py             # Core LLM agent logic
│   └── llm_app.py           # FastAPI application for the LLM service
│   └── tool.py              # Tools/functions used by the LLM agent
├── web-app/                 # Web application (user interface)
│   ├── Dockerfile           # Container configuration
│   ├── requirements.txt     # Python dependencies
│   ├── app.py               # FastAPI application for the web UI
│   └── templates/           # HTML templates for the web UI
│       ├── index.html
│       ├── detail.html
│       └── trending.html
├── docker-compose.yml       # Docker Compose configuration
├── LICENSE                  # Project License
├── pyproject.toml           # Python project configuration
└── README.md                
```

## Setup and Configuration

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/software-students-spring2025/5-final-galaxy.git
    cd 5-final-galaxy
    ```

2.  **Environment Variables:**

    Create a `.env` file in the project root directory by copying the structure from `.env.example` . Fill in the required values. Based on the `docker-compose.yml`, you will need at least the following variables:

    ```bash
    # .env
    # Example MongoDB connection string
    MONGO_URI=mongodb://mongodb:27017/stockDB 
    # Choose your preferred LLM provider (Choose from OPENAI, GEMINI, XAI)              
    LLM_API_PROVIDER=OPENAI
    # Your API key for the LLM provider
    OPENAI_API_KEY=YOUR_OPENAI_API_KEY        
    GEMINI_API_KEY=YOUR_GEMINI_API_KEY        
    XAI_API_KEY=YOUR_XAI_API_KEY      
    ```


3.  **Docker:**
    Ensure you have Docker and Docker Compose installed on your system.

## Running the Project

1.  **Build and Run Containers:**
    From the project root directory, run:
    ```bash
    docker-compose up --build -d
    ```

2.  **Accessing the Application:**
    -   The Web App should be accessible at `http://localhost:5001`.
    -   The LLM service runs internally and is accessed by the Web App at `http://llm:5002`.
    -   The MongoDB database is accessible on the host machine at `mongodb://localhost:27017` if needed for direct inspection, but primarily used internally by the services.

3.  **Stopping the Application:**
    To stop the running containers, execute:
    ```bash
    docker-compose down
    ```
