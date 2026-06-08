"""
Application Entry Point

This is the main script to start the FastAPI web server.
It uses uvicorn (a fast ASGI server) to run the application.

HOW TO RUN:
    python run.py

WHAT IT DOES:
    1. Imports the FastAPI app from main.py
    2. Starts a web server on port 3000
    3. Enables auto-reload for development (server restarts when code changes)

WHY SEPARATE FILE:
    Separating the entry point from the app definition follows the
    Single Responsibility Principle:
    - main.py: Defines and configures the app
    - run.py: Only starts the server
"""

import uvicorn

# This block only runs when this file is executed directly (not imported)
# WHY: Prevents the server from starting when this file is imported by tests
if __name__ == "__main__":
    uvicorn.run(
        "main:app",        # Points to the 'app' variable in main.py
        host="0.0.0.0",    # Listen on all network interfaces (allows external access)
        port=3000,         # Port number for the web server
        reload=True,       # Auto-restart server when code changes (development only)
    )
