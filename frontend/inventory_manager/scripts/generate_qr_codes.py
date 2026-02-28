#!/usr/bin/env python3
"""
Generate QR codes for Docker and ngrok URLs
"""
import os
import sys
from pathlib import Path

try:
    import qrcode
except ImportError:
    print("Installing qrcode library...")
    os.system(f"{sys.executable} -m pip install qrcode[pil] --quiet")
    import qrcode

# URLs
NGROK_URL = "https://unenriching-janice-unpermanent.ngrok-free.dev"
DOCKER_COMMAND = "docker run -p 8000:8000 -e DEMO_MODE=false donxera-inventory"
DOCKER_INFO = "Docker: localhost:8000"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "assets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_qr_code(data: str, filename: str, label: str = None):
    """Generate a QR code image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    output_path = OUTPUT_DIR / filename
    img.save(output_path)
    print(f"✅ Generated {label or filename}: {output_path}")
    return output_path

if __name__ == "__main__":
    print("🎨 Generating QR Codes...")
    print()
    
    # Generate ngrok QR code
    generate_qr_code(NGROK_URL, "qr_ngrok.png", "ngrok QR Code")
    
    # Generate Docker localhost QR code  
    generate_qr_code("http://localhost:8000", "qr_docker.png", "Docker Local QR Code")
    
    # Generate Docker command QR code (optional)
    generate_qr_code(DOCKER_COMMAND, "qr_docker_command.png", "Docker Command QR Code")
    
    print()
    print("✨ All QR codes generated successfully!")
    print(f"📁 Location: {OUTPUT_DIR}")
