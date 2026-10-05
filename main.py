"""
Root entrypoint for Nvirya AI Gateway.
Compatible with direct execution (python main.py), Uvicorn (uvicorn main:app),
and shared hosting environments (cPanel Python App).
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.main import app

# Canonical entrypoint alias for shared hosts expecting 'application' or 'app'
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
