"""The AI Architect Panel - Main Entry Point.

Run the API server:
    python run.py api

Run the CLI:
    python run.py cli run "I need a HIPAA-compliant patient data pipeline" --region india

Run interactive CLI:
    python run.py cli interactive

View sessions:
    python run.py cli list
"""

from __future__ import annotations
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import settings


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python run.py api                          # Start API server")
        print("  python run.py cli run [prompt]              # Run a single session")
        print("  python run.py cli interactive               # Interactive CLI mode")
        print("  python run.py cli list                      # List sessions")
        return

    command = sys.argv[1]

    if command == "api":
        import uvicorn
        port = int(os.getenv("PORT", "8000"))
        print(f"Starting {settings.app_name} API on port {port}")
        uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=True)

    elif command == "cli":
        from src.cli.main import run_cli
        # Forward remaining arguments (skip 'cli' arg)
        run_cli(sys.argv[2:])

    else:
        print(f"Unknown command: {command}")
        print("Use: api, cli, or interactive")


if __name__ == "__main__":
    main()
