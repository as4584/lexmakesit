#!/usr/bin/env python3
"""
Smart Flask + ngrok Startup Script
Detects running Flask app, starts if needed, and connects ngrok tunnel.
Handles ERR_NGROK_8012 and other connection issues with helpful diagnostics.
"""
import os
import sys
import time
import socket
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment from .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class SmartStarter:
    """Intelligent Flask + ngrok startup with diagnostics."""
    
    def __init__(self):
        self.flask_port = int(os.getenv('PORT', 5000))
        self.domain = os.getenv('NGROK_DOMAIN', 'unenriching-janice-unpermanent.ngrok-free.dev')
        self.authtoken = os.getenv('NGROK_AUTHTOKEN') or os.getenv('NGROK_AUTH_TOKEN')
        self.flask_process = None
        self.ngrok_process = None
        
    def is_port_in_use(self, port):
        """Check if a port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def get_process_on_port(self, port):
        """Get process info for what's using a port."""
        try:
            result = subprocess.run(
                ['lsof', '-i', f':{port}', '-t'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pid = result.stdout.strip().split('\n')[0]
                proc_info = subprocess.run(
                    ['ps', '-p', pid, '-o', 'comm='],
                    capture_output=True,
                    text=True
                )
                return proc_info.stdout.strip()
        except Exception:
            pass
        return None
    
    def test_flask_connection(self, port, max_retries=5):
        """Test if Flask app is responding."""
        for i in range(max_retries):
            try:
                response = requests.get(f'http://localhost:{port}/health', timeout=2)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                if i < max_retries - 1:
                    time.sleep(1)
        return False
    
    def start_flask_app(self):
        """Start Flask app if not already running."""
        print(f"\n🔍 Checking if Flask is running on port {self.flask_port}...")
        
        if self.is_port_in_use(self.flask_port):
            process = self.get_process_on_port(self.flask_port)
            print(f"✅ Port {self.flask_port} is in use by: {process or 'unknown process'}")
            
            # Test if it's actually Flask
            if self.test_flask_connection(self.flask_port):
                print(f"✅ Flask app is responding on port {self.flask_port}")
                return True
            else:
                print(f"⚠️  Port {self.flask_port} is busy but not responding to Flask health check")
                print(f"💡 Solution: Kill the process and restart:")
                print(f"   sudo lsof -ti:{self.flask_port} | xargs kill -9")
                return False
        
        print(f"❌ Flask not running on port {self.flask_port}")
        print(f"🚀 Starting Flask app...")
        
        try:
            repo_root = Path(__file__).parent.parent
            env = os.environ.copy()
            env['PYTHONPATH'] = str(repo_root / 'src')
            env['DEMO_MODE'] = 'true'
            env['PORT'] = str(self.flask_port)
            env['ENABLE_NGROK'] = 'false'  # Prevent recursive ngrok start
            
            self.flask_process = subprocess.Popen(
                ['python3', str(repo_root / 'scripts' / 'run_local.py')],
                cwd=str(repo_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for Flask to start
            print(f"⏳ Waiting for Flask to start...")
            time.sleep(3)
            
            if self.test_flask_connection(self.flask_port, max_retries=10):
                print(f"✅ Flask started successfully on port {self.flask_port}")
                return True
            else:
                print(f"❌ Flask started but not responding")
                print(f"💡 Check if port {self.flask_port} is blocked or app has errors")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start Flask: {e}")
            return False
    
    def create_ngrok_config(self):
        """Create ngrok.yml configuration file."""
        ngrok_config_dir = Path.home() / '.config' / 'ngrok'
        ngrok_config_dir.mkdir(parents=True, exist_ok=True)
        ngrok_config_path = ngrok_config_dir / 'ngrok.yml'
        
        config_content = f"""version: "3"
agent:
  authtoken: {self.authtoken}
tunnels:
  flask-app:
    proto: http
    addr: {self.flask_port}
    domain: {self.domain}
"""
        
        try:
            with open(ngrok_config_path, 'w') as f:
                f.write(config_content)
            print(f"✅ Created ngrok config: {ngrok_config_path}")
            return str(ngrok_config_path)
        except Exception as e:
            print(f"⚠️  Could not create ngrok config: {e}")
            return None
    
    def configure_ngrok(self):
        """Configure ngrok with authtoken."""
        if not self.authtoken:
            print("❌ NGROK_AUTHTOKEN not found in .env file!")
            print("💡 Add this to your .env file:")
            print("   NGROK_AUTHTOKEN=your_token_here")
            return False
        
        print(f"🔧 Configuring ngrok with authtoken from .env...")
        try:
            result = subprocess.run(
                ['ngrok', 'config', 'add-authtoken', self.authtoken],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ ngrok authtoken configured")
            
            # Also create ngrok.yml
            self.create_ngrok_config()
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to configure ngrok authtoken")
            print(f"Error: {e.stderr}")
            return False
    
    def start_ngrok(self):
        """Start ngrok tunnel with diagnostics."""
        print(f"\n🌐 Starting ngrok tunnel...")
        print(f"Domain: {self.domain}")
        print(f"Forwarding to: localhost:{self.flask_port}")
        
        # Configure first
        if not self.configure_ngrok():
            return False
        
        # Check if ngrok is already running
        try:
            response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=1)
            if response.status_code == 200:
                tunnels = response.json().get('tunnels', [])
                if tunnels:
                    print(f"♻️  ngrok is already running")
                    for tunnel in tunnels:
                        print(f"   {tunnel['public_url']} -> {tunnel['config']['addr']}")
                    return True
        except Exception:
            pass
        
        try:
            cmd = ['ngrok', 'http', str(self.flask_port), '--domain', self.domain]
            self.ngrok_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for ngrok to start
            print(f"⏳ Waiting for ngrok tunnel...")
            time.sleep(3)
            
            # Verify tunnel
            public_url = self.get_ngrok_url()
            if public_url:
                print(f"\n{'='*60}")
                print(f"🎉 SUCCESS! Your app is live!")
                print(f"{'='*60}")
                print(f"🌐 PUBLIC URL: {public_url}")
                print(f"📱 Share this URL with anyone!")
                print(f"{'='*60}\n")
                return True
            else:
                print(f"⚠️  ngrok started but no tunnel detected")
                self.diagnose_ngrok_error()
                return False
                
        except Exception as e:
            print(f"❌ Failed to start ngrok: {e}")
            self.diagnose_ngrok_error()
            return False
    
    def get_ngrok_url(self, max_retries=10):
        """Get public URL from ngrok API."""
        for i in range(max_retries):
            try:
                response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=2)
                if response.status_code == 200:
                    tunnels = response.json().get('tunnels', [])
                    for tunnel in tunnels:
                        if tunnel['proto'] == 'https':
                            return tunnel['public_url']
                    if tunnels:
                        return tunnels[0]['public_url']
            except Exception:
                if i < max_retries - 1:
                    time.sleep(1)
        return None
    
    def diagnose_ngrok_error(self):
        """Provide helpful diagnostics for ngrok errors."""
        print(f"\n🔍 DIAGNOSING ngrok CONNECTION ISSUE...\n")
        
        # Check if Flask is accessible
        if not self.is_port_in_use(self.flask_port):
            print(f"❌ Flask app not running on port {self.flask_port}")
            print(f"💡 Solution: Restart Flask app")
            return
        
        # Check Flask health
        if not self.test_flask_connection(self.flask_port):
            print(f"❌ Flask port is open but app not responding")
            print(f"💡 Solution: Check Flask app logs for errors")
            return
        
        # Check ngrok process
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'ngrok'],
                capture_output=True,
                text=True
            )
            if not result.stdout.strip():
                print(f"❌ ngrok process not running")
                print(f"💡 Solution: ngrok may have crashed, check installation")
                return
        except Exception:
            pass
        
        print(f"⚠️  Common issues:")
        print(f"   1. ERR_NGROK_8012 - Connection refused")
        print(f"      → Flask not accepting connections")
        print(f"      → Check firewall/security settings")
        print(f"   2. Invalid authtoken")
        print(f"      → Verify NGROK_AUTHTOKEN in .env")
        print(f"   3. Domain not available")
        print(f"      → Check domain at dashboard.ngrok.com")
        print(f"\n💡 Try:")
        print(f"   1. Test Flask: curl http://localhost:{self.flask_port}/health")
        print(f"   2. Check ngrok logs: http://127.0.0.1:4040")
        print(f"   3. Verify domain: https://dashboard.ngrok.com/cloud-edge/domains")
    
    def run(self):
        """Run the complete startup sequence."""
        print("="*60)
        print("🚀 SMART FLASK + ngrok STARTER")
        print("="*60)
        
        # Step 1: Ensure Flask is running
        if not self.start_flask_app():
            print("\n❌ Cannot proceed without Flask app")
            return False
        
        # Step 2: Start ngrok
        if not self.start_ngrok():
            print("\n❌ ngrok tunnel failed to start")
            return False
        
        print("\n✅ All systems running!")
        print("\nKeep this terminal open to maintain the connection.")
        print("Press Ctrl+C to stop.\n")
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down...")
            if self.flask_process:
                self.flask_process.terminate()
            if self.ngrok_process:
                self.ngrok_process.terminate()
            print("✅ Stopped")
        
        return True


if __name__ == '__main__':
    starter = SmartStarter()
    success = starter.run()
    sys.exit(0 if success else 1)
