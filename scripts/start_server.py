#!/usr/bin/env python3
"""
Production WSGI server for Jalaram CNC using Waitress.
This is what NSSM runs as the Windows Service.

Usage:
    python scripts/start_server.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jalaram_cnc.settings')

# Load .env
env_file = PROJECT_ROOT / '.env'
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        pass

if __name__ == '__main__':
    # Django setup must happen after env vars are loaded
    import django
    django.setup()

    from waitress import serve
    from django.core.handlers.wsgi import WSGIHandler

    application = WSGIHandler()

    host = os.environ.get('SERVER_HOST', '127.0.0.1')
    port = int(os.environ.get('SERVER_PORT', '8000'))

    print(f"[Jalaram CNC] Starting server on http://{host}:{port}", flush=True)
    print("[Jalaram CNC] Press Ctrl+C to stop.", flush=True)

    serve(
        application,
        host=host,
        port=port,
        threads=4,
        channel_timeout=60,
        cleanup_interval=30,
    )
