#!/usr/bin/env python3
"""
Professional Inventory Management System - Development Server
"""
import os
import sys
from pathlib import Path

# Add src/ to Python path for development
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / 'src'))

from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

def create_app():
    """Create and configure the Flask application for development."""
    try:
        from app import create_app as app_factory
        return app_factory()
    except ImportError as e:
        print(f"Error importing app: {e}")
        sys.exit(1)

def main():
    """Run the development server."""
    app = create_app()
    
    # Development configuration
    port = int(os.getenv('PORT', 8010))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"🚀 Starting Professional Inventory Management System")
    print(f"📍 Development server: http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"💼 Environment: {os.getenv('FLASK_ENV', 'development')}")
    
    # For compatibility with gunicorn
    app.config['DEBUG'] = debug
    
    try:
        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=debug,
            use_reloader=debug
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down development server...")

# For gunicorn compatibility
app = create_app()

if __name__ == '__main__':
    main()
