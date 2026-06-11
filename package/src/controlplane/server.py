import logging
import sys
from typing import Dict
from fastapi import FastAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("ostrich-controlplane")

# Instantiate FastAPI application
app = FastAPI(
    title="Ostrich Chatbot API",
    description="Backend services for the Ostrich Chatbot platform",
    version="0.1.0",
)


@app.get("/health", status_code=200)
def health_check() -> Dict[str, str]:
    """Health check endpoint to verify that the service is running.

    Returns:
        A dictionary containing the status of the application.
    """
    logger.info("Health check endpoint hit")
    return {"status": "healthy"}
