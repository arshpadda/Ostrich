import logging

import uvicorn

logger = logging.getLogger("ostrich-app")

def start() -> None:
    """Entry point function to run the application locally with Uvicorn."""
    logger.info("Starting Ostrich application...")
    uvicorn.run("src.controlplane.server:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()
