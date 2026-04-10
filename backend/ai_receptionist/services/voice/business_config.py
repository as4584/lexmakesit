"""
Business configuration for LexMakesIt.

AI-powered receptionist solutions for businesses.

Note: Contact information should be loaded from environment variables
in production. These are defaults for development/testing.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ===== BUSINESS IDENTITY =====
BUSINESS_NAME = "LexMakesIt"

# ===== SERVICES OFFERED =====
SERVICES = [
    {"name": "AI Receptionist", "price": "Custom plans available"},
    {"name": "24/7 Call Answering", "price": "Included with AI Receptionist"},
    {"name": "Appointment Scheduling", "price": "Included with AI Receptionist"},
    {"name": "Missed Call Recovery", "price": "Included with AI Receptionist"},
    {"name": "Custom Voice Cloning", "price": "Pro plan"},
    {"name": "Bilingual Support (EN/ES)", "price": "Included"},
    {"name": "CRM & Calendar Integration", "price": "Included"},
]

# ===== BUSINESS HOURS =====
HOURS = {
    "weekday": "Monday – Friday: 9:00 AM – 6:00 PM",
    "weekend": "Saturday: By appointment | Sunday: Closed",
    "notes": "Our AI Receptionist answers calls 24/7 — even when the office is closed!",
}

# ===== STAFF =====
STAFF = [
    {"role": "Founder & CEO", "name": "Alexander Santiago"},
    {"role": "AI Receptionist", "name": "Aria (that's me!)"},
]

# ===== OFFICE LOCATION(S) =====
LOCATION = "Career Fair Demo — LexMakesIt"

# ===== CONTACT INFO =====
# These should ideally come from environment variables in production
PHONE: Optional[str] = "+12298215986"
EMAIL = "thegamermasterninja@gmail.com"

# ===== ESCALATION =====
ESCALATION_CONTACT = "Alexander Santiago"
ESCALATION_PHONE: Optional[str] = "+12298215986"


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
