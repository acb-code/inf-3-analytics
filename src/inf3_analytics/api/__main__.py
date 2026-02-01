"""Entry point for running the API server."""

import uvicorn

from inf3_analytics.api.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
