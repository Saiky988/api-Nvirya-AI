"""
cPanel / Phusion Passenger WSGI/ASGI entrypoint for shared hosting.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app

# If Passenger operates in WSGI mode, wrap ASGI app with a2wsgi adapter
try:
    from a2wsgi import ASGIMiddleware
    application = ASGIMiddleware(app)
except ImportError:
    # If a2wsgi is not present or host supports ASGI natively
    application = app
