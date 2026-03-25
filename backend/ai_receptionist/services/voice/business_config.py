"""
Business configuration for Innovation Business Development Solutions.

National business infrastructure firm — formation, licensing, digital systems,
and compliance, coordinated as one integrated platform across all 50 states.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ===== BUSINESS IDENTITY =====
BUSINESS_NAME = "Innovation Business Development Solutions"

# ===== SERVICES OFFERED =====
SERVICES = [
    {"name": "Business Formation and LLC Setup", "price": "varies by state"},
    {"name": "Multi-State Licensing and Compliance", "price": "varies"},
    {"name": "Website and Growth Infrastructure", "price": "varies"},
    {"name": "Custom Applications and Software", "price": "varies"},
    {"name": "AI Systems and Automation", "price": "varies"},
    {"name": "Digital Communication Setup", "price": "varies"},
]

# ===== BUSINESS HOURS =====
HOURS = {
    "weekday": "Monday – Friday: 9:00 AM – 6:00 PM",
    "weekend": "Saturday: By appointment",
    "notes": "We serve clients across all 50 states remotely",
}

# ===== STAFF =====
STAFF = [
    {"role": "Founder", "name": "Damian"},
    {"role": "Business Development Team", "name": "Available to assist you"},
]

# ===== OFFICE LOCATION(S) =====
LOCATION = "Serving all 50 states"

# ===== CONTACT INFO =====
PHONE: Optional[str] = None  # Load from settings in production
EMAIL = "info@innovationbusinessservices.com"

# ===== ESCALATION =====
ESCALATION_CONTACT = "Business Development Team"
ESCALATION_PHONE: Optional[str] = None  # Load from settings in production

# ===== WEBSITE CONTEXT (populated by Learn from Website feature) =====
WEBSITE_CONTEXT: Optional[str] = None
WEBSITE_URL: Optional[str] = None


def get_phone_number() -> str:
    """
    Get business phone number, with fallback to environment.
    
    Returns:
        Phone number string
    """
    if PHONE:
        return PHONE
    
    try:
        from ai_receptionist.config import get_settings
        settings = get_settings()
        return settings.twilio_phone_number or "Contact office"
    except Exception as e:
        logger.warning(f"Could not load phone from settings: {e}")
        return "Contact office"


def get_escalation_phone() -> str:
    """
    Get escalation phone number, with fallback to environment.
    
    Returns:
        Escalation phone number string
    """
    if ESCALATION_PHONE:
        return ESCALATION_PHONE
    
    return get_phone_number()  # Default to main phone
