#!/usr/bin/env python3
"""
ngrok Tunnel Manager
Automatically starts ngrok tunnel with reserved domain when Flask app starts.
Detects existing tunnels and reuses them when possible.
"""
import os
import subprocess
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class NgrokTunnel:
    """Manages ngrok tunnel lifecycle with smart detection and reuse."""
    
    def __init__(self, port=5000, domain=None):
        self.port = port
        self.domain = domain
        self.authtoken = os.getenv('NGROK_AUTH_TOKEN') or os.getenv('NGROK_AUTHTOKEN')
        self.process = None
        self.public_url = None
        self.reused_tunnel = False
        
    def is_ngrok_running(self):
        """Check if ngrok process is already running."""
        try:
            # Check if ngrok API is accessible
            response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=1)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_existing_tunnel(self):
        """Get existing tunnel info if ngrok is already running."""
        try:
            response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=2)
            if response.status_code == 200:
                tunnels = response.json().get('tunnels', [])
                
                # Look for tunnel matching our port
                for tunnel in tunnels:
                    config = tunnel.get('config', {})
                    if config.get('addr', '').endswith(f':{self.port}'):
                        return tunnel
                
                # Return any HTTPS tunnel if port doesn't match
                for tunnel in tunnels:
                    if tunnel['proto'] == 'https':
                        return tunnel
                        
                # Return first tunnel
                if tunnels:
                    return tunnels[0]
        except Exception:
            pass
        return None
    
    def configure_authtoken(self):
        """Configure ngrok with authtoken from environment."""
        if not self.authtoken:
            raise ValueError("NGROK_AUTH_TOKEN not found in .env file")
        
        try:
            subprocess.run(
                ['ngrok', 'config', 'add-authtoken', self.authtoken],
                check=True,
                capture_output=True
            )
            print("✅ ngrok authtoken configured")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to configure authtoken: {e}")
            return False
    
    def start_tunnel(self):
        """Start ngrok tunnel with reserved domain, or reuse existing tunnel."""
        
        # First check if ngrok is already running
        if self.is_ngrok_running():
            existing = self.get_existing_tunnel()
            if existing:
                self.public_url = existing.get('public_url')
                self.reused_tunnel = True
                
                print(f"♻️  Found existing ngrok tunnel!")
                print(f"\n{'='*60}")
                print(f"🌐 PUBLIC URL: {self.public_url}")
                print(f"📱 Share this with your cousin!")
                print(f"{'='*60}\n")
                return True
        
        try:
            # Configure authtoken first
            if not self.configure_authtoken():
                return False
            
            # Build ngrok command
            if self.domain:
                cmd = ['ngrok', 'http', str(self.port), '--domain', self.domain]
                print(f"🚀 Starting ngrok tunnel with domain: {self.domain}")
            else:
                cmd = ['ngrok', 'http', str(self.port)]
                print(f"🚀 Starting ngrok tunnel on port {self.port}")
            
            # Start ngrok in background
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for ngrok to start
            time.sleep(3)
            
            # Get public URL from ngrok API
            self.public_url = self.get_public_url()
            
            if self.public_url:
                print(f"\n{'='*60}")
                print(f"🌐 PUBLIC URL: {self.public_url}")
                print(f"📱 Share this with your cousin!")
                print(f"{'='*60}\n")
                return True
            else:
                print("⚠️  Could not retrieve public URL")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start ngrok: {e}")
            return False
    
    def get_public_url(self, retries=5):
        """Get public URL from ngrok local API."""
        for i in range(retries):
            try:
                response = requests.get('http://127.0.0.1:4040/api/tunnels')
                if response.status_code == 200:
                    tunnels = response.json().get('tunnels', [])
                    if tunnels:
                        # Get HTTPS URL
                        for tunnel in tunnels:
                            if tunnel['proto'] == 'https':
                                return tunnel['public_url']
                        # Fallback to first tunnel
                        return tunnels[0]['public_url']
            except requests.exceptions.RequestException:
                time.sleep(1)
        return None
    
    def stop_tunnel(self):
        """Stop ngrok tunnel only if we started it (don't kill reused tunnels)."""
        if self.reused_tunnel:
            print("ℹ️  Keeping existing ngrok tunnel running")
            return
            
        if self.process:
            self.process.terminate()
            self.process.wait()
            print("🛑 ngrok tunnel stopped")
    
    def is_running(self):
        """Check if ngrok is running."""
        return self.process and self.process.poll() is None


def start_ngrok_with_flask(port=5000, domain=None):
    """
    Start ngrok tunnel for Flask app.
    
    Args:
        port: Flask app port (default: 5000)
        domain: Reserved ngrok domain (optional)
    
    Returns:
        NgrokTunnel instance
    """
    tunnel = NgrokTunnel(port=port, domain=domain)
    
    if tunnel.start_tunnel():
        return tunnel
    else:
        print("⚠️  Running without ngrok tunnel")
        return None


if __name__ == '__main__':
    # Test the tunnel
    RESERVED_DOMAIN = "unenriching-janice-unpermanent.ngrok-free.dev"
    
    print("🧪 Testing ngrok tunnel configuration...")
    tunnel = start_ngrok_with_flask(port=5000, domain=RESERVED_DOMAIN)
    
    if tunnel:
        print("\n✅ Tunnel is running!")
        print(f"Public URL: {tunnel.public_url}")
        print("\nPress Ctrl+C to stop...")
        
        try:
            while tunnel.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping tunnel...")
            tunnel.stop_tunnel()
    else:
        print("❌ Failed to start tunnel")
