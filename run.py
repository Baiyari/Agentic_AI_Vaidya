import sys
import argparse
import multiprocessing
import logging
from api import create_app
from config.settings import settings
from mcp_server import run_mcp_server

logger = logging.getLogger(__name__)

def run_flask():
    """Runs the Flask REST API."""
    app = create_app()
    app.run(host=settings.FLASK_HOST, port=settings.FLASK_PORT, debug=False, use_reloader=False)

def run_mcp():
    """Runs the FastMCP server."""
    run_mcp_server()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vaidya Backend Services Runner")
    parser.add_argument(
        "--service",
        choices=["api", "mcp", "all"],
        default="all",
        help="Service to start: api, mcp, or all (default: all)"
    )
    args = parser.parse_args()

    # Configure root logging for the main process
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    logger.info(f"Starting Vaidya Backend (mode: {args.service})...")

    if args.service == "api":
        logger.info(f"Starting Flask API on {settings.FLASK_HOST}:{settings.FLASK_PORT}...")
        run_flask()
    elif args.service == "mcp":
        logger.info(f"Starting MCP Server on {settings.MCP_HOST}:{settings.MCP_PORT}...")
        run_mcp()
    else:
        # Start Flask API in a separate process
        flask_process = multiprocessing.Process(target=run_flask, name="Flask-API")
        flask_process.start()
        logger.info(f"Flask API started on {settings.FLASK_HOST}:{settings.FLASK_PORT}")

        # Start MCP Server in a separate process
        mcp_process = multiprocessing.Process(target=run_mcp, name="MCP-Server")
        mcp_process.start()
        logger.info(f"MCP Server started on {settings.MCP_HOST}:{settings.MCP_PORT}")

        try:
            flask_process.join()
            mcp_process.join()
        except KeyboardInterrupt:
            logger.info("Shutting down Vaidya Backend Services...")
            flask_process.terminate()
            mcp_process.terminate()
            flask_process.join()
            mcp_process.join()
            logger.info("Shutdown complete.")
