"""Deal Intelligence Agent — an AI sales assistant with persistent memory."""
from pathlib import Path

from dotenv import load_dotenv

# Load settings for both uvicorn and command-line entry points; shell values win.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
