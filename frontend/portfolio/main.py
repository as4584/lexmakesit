import mimetypes
mimetypes.init()
mimetypes.add_type('image/webp', '.webp')
mimetypes.types_map['.webp'] = 'image/webp'

import json
import logging
import logging.handlers
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

import aiosmtplib
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import storage
import abuse_guard

# Admin access for the blog editor. There is no user table and no signup:
# one operator, one password hash supplied by the environment. If no hash
# is configured the admin surface stays closed rather than falling back to
# a default credential.
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH") or ""
ADMIN_PASSWORD_HASH_FILE = os.getenv("ADMIN_PASSWORD_HASH_FILE")
if not ADMIN_PASSWORD_HASH and ADMIN_PASSWORD_HASH_FILE:
    try:
        with open(ADMIN_PASSWORD_HASH_FILE, "r", encoding="utf-8") as _fh:
            ADMIN_PASSWORD_HASH = _fh.read().strip()
    except OSError:
        ADMIN_PASSWORD_HASH = ""
ADMIN_SESSION_HOURS = int(os.getenv("ADMIN_SESSION_HOURS", "12"))

# Load environment variables securely
load_dotenv()

# Create logs directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


class StructuredFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            ):
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


# Configure structured logging
def setup_logging():
    """Setup structured logging with file rotation and console output"""

    # Remove default handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create formatters
    structured_formatter = StructuredFormatter()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler for all environments
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # File handlers only if we can write to the directory
    try:
        log_dir.mkdir(mode=0o755, exist_ok=True)

        # Test if we can write to the directory
        test_file = log_dir / "test.tmp"
        test_file.touch()
        test_file.unlink()

        # File handler for structured logs
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "application.json",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,  # 10MB
        )
        file_handler.setFormatter(structured_formatter)

        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "errors.json", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        error_handler.setFormatter(structured_formatter)
        error_handler.setLevel(logging.ERROR)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)

        logging.info(f"File logging enabled in {log_dir}")

    except (PermissionError, OSError) as e:
        logging.warning(
            f"File logging disabled due to permissions: {e}. Using console only."
        )
        # Continue with just console logging

    # Set third-party library log levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


# Security configurations from environment
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", "30"))
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "https://lexmakesit.com,https://www.lexmakesit.com"
).split(",")
TRUSTED_HOSTS = os.getenv(
    "TRUSTED_HOSTS",
    "localhost,127.0.0.1,104.236.100.245,104.236.100.245:8000,testserver,lexmakesit.com,www.lexmakesit.com",
).split(",")
PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_PER_MINUTE = os.getenv("RATE_LIMIT_PER_MINUTE", "60") or "60"
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST") or "10")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
DEFAULT_RATE_LIMIT_STORAGE = (
    f"redis://:{REDIS_PASSWORD}@redis:6379/1"
    if REDIS_PASSWORD
    else "redis://redis:6379/1"
)
RATE_LIMIT_STORAGE = os.getenv("RATE_LIMIT_STORAGE", DEFAULT_RATE_LIMIT_STORAGE)

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = os.getenv("SMTP_USER") or ""
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or ""
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Portfolio Contact")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
CONTACT_RECIPIENT_EMAIL = os.getenv("CONTACT_RECIPIENT_EMAIL", "as42519256@gmail.com")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Global application state
db_pool = None


async def get_db_pool():
    """Get database connection pool - disabled for database-independent operation"""
    return None


async def close_db_pool():
    """Close database connection pool - safe no-op for database-independent operation"""
    # No database operations needed in database-independent mode
    logger.info("Database operations disabled - no cleanup required")


# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    try:
        # Durable storage is optional: if the database is unreachable the
        # site still serves every page, it just cannot record submissions.
        storage_ready = await storage.init_pool()
        logger.info(
            "Application startup complete - durable storage %s",
            "enabled" if storage_ready else "unavailable",
        )
    except Exception as e:
        logger.error(f"Failed to startup application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await storage.close_pool()
    await close_db_pool()
    logger.info("Application shutdown complete")


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def client_ip_key(request: Request) -> str:
    """Per-client key for rate limiting.

    The only route into this app is the Cloudflare Tunnel, so every request
    reaches the container from the cloudflared sidecar and
    get_remote_address() returns the SAME address for the entire internet.
    Keying on that made every limit global instead of per-client: one client
    could exhaust the shared budget and deny everyone else, and /api/contact's
    5/hour applied to all visitors combined.

    Cloudflare sets CF-Connecting-IP to the true client address. It is only
    safe to trust a client-supplied header when the request cannot arrive by
    any other path - which holds here: the container publishes nothing except
    127.0.0.1 diagnostics, and the tunnel is outbound-only. Fall back to the
    first X-Forwarded-For hop, then the socket peer (loopback diagnostics).
    """
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return get_remote_address(request)


# Rate limiting with configurable thresholds for security
limiter = Limiter(
    key_func=client_ip_key,
    default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=RATE_LIMIT_STORAGE,
)

# Initialize FastAPI app with security defaults and lifespan
app = FastAPI(
    title="LexMakesIt AI Receptionist",
    description="Smarter 24/7 AI Phone system for small businesses. Handles inquiries, books appointments, and captures leads.",
    version="1.3.0",  # Updated for Google OAuth compliance
    docs_url=None if PRODUCTION else "/api/docs",  # Hide docs in production
    redoc_url=None if PRODUCTION else "/api/redoc",
    openapi_url=None if PRODUCTION else "/openapi.json",
    lifespan=lifespan,
)

# Apple Pay Domain Verification Route
@app.get("/.well-known/apple-developer-merchantid-domain-association")
async def apple_pay_verification():
    """Serve Apple Pay domain verification file"""
    file_path = os.path.join("static", ".well-known", "apple-developer-merchantid-domain-association")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"detail": "Verification file not found. Please upload it to static/.well-known/"})

# Apply rate limiting with exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration - Restrict to allowed origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict to needed methods only
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# Trusted Host Middleware - Use environment configuration
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS
)


# ============================================================================
# OWASP ASVS LEVEL 1 SECURITY HEADERS MIDDLEWARE
# ============================================================================
@app.middleware("http")
async def abuse_guard_middleware(request: Request, call_next):
    """Turn away clients that keep tripping the rate limits.

    Only /api/ paths are considered. Pages are always served: a visitor
    who annoyed the rate limiter should still be able to read the site.
    """
    path = request.url.path
    if path.startswith("/api/"):
        client = client_ip_key(request)
        blocked, remaining = abuse_guard.is_blocked(client)
        if blocked:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "message": (
                        "Too many requests from this address. Try again in "
                        f"{max(1, remaining // 60)} minute(s)."
                    )
                },
                headers={"Retry-After": str(remaining)},
            )

    response = await call_next(request)

    # A 429 from the limiter is a strike; enough strikes earn a timeout.
    if path.startswith("/api/") and response.status_code == 429:
        abuse_guard.record_strike(client_ip_key(request))

    return response


@app.middleware("http")
async def static_cache_middleware(request: Request, call_next):
    """Cache policy for /static.

    Cloudflare was caching stylesheets for four hours (observed
    cf-cache-status: HIT with Age 5498 against max-age=14400). A deploy
    therefore shipped new HTML while visitors kept the old CSS for hours —
    which renders as a subtly broken page rather than an obvious failure.

    Code assets must revalidate on every request: the ETag makes that a
    cheap 304, so the cost is a round trip rather than a re-download.
    Media keeps a long TTL because those files are replaced by name, not
    edited in place.
    """
    response = await call_next(request)

    path = request.url.path
    if path.startswith("/static/"):
        if path.endswith((".css", ".js")):
            response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
        elif path.endswith((".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                            ".woff", ".woff2", ".ico")):
            response.headers["Cache-Control"] = "public, max-age=604800"

    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    Enforce comprehensive security headers per OWASP recommendations:
    - CSP: Prevent XSS and code injection
    - HSTS: Force HTTPS on all future visits
    - X-Frame-Options: Prevent clickjacking
    - X-Content-Type-Options: Prevent MIME sniffing
    - Referrer-Policy: Control referrer information leakage
    - Permissions-Policy: Disable unnecessary browser features
    """
    response = await call_next(request)

    # Content Security Policy (strict, allow only trusted sources)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    # HTTP Strict Transport Security (force HTTPS)
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Clickjacking protection
    response.headers["X-Frame-Options"] = "DENY"

    # XSS filter (legacy browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer policy (limit information leakage)
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions policy (disable unnecessary features)
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=()"
    )

    # Remove server identification header (use del instead of pop for MutableHeaders)
    if "server" in response.headers:
        del response.headers["server"]

    return response


# Request size limiter middleware (prevent DoS via large payloads)
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Prevent DoS attacks via oversized request bodies"""
    max_size = 1024 * 1024  # 1 MB limit
    content_length = request.headers.get("content-length")

    if content_length and int(content_length) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Request body too large",
        )

    return await call_next(request)


# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ============================================================================
# PYDANTIC MODELS WITH INPUT VALIDATION & SANITIZATION (OWASP)
# ============================================================================


class WaitlistSignup(BaseModel):
    """Email-only signup for an unreleased product."""

    email: EmailStr
    product: str = "reseller"

    @field_validator("product")
    @classmethod
    def validate_product(cls, v: str) -> str:
        allowed = {"reseller", "agentop", "bakerypos"}
        v = (v or "reseller").strip().lower()
        if v not in allowed:
            raise ValueError("Unknown product")
        return v


class ContactForm(BaseModel):
    """
    Secure contact form with comprehensive input validation:
    - Length limits to prevent buffer overflow
    - Character whitelist to prevent injection
    - Email validation via EmailStr
    - HTML/script tag stripping
    """

    name: str
    email: EmailStr
    subject: Optional[str] = "lexmakesit email"
    message: str

    @field_validator("name", "subject")
    @classmethod
    def validate_text_field(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize text fields: strip, length check, no HTML"""
        if v is None:
            return v
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")

        v = v.strip()

        # Length validation
        if len(v) < 2:
            raise ValueError("Field must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Field cannot exceed 100 characters")

        # Prevent HTML/script injection
        dangerous_chars = ["<", ">", "{", "}", "`", "$"]
        if any(char in v for char in dangerous_chars):
            raise ValueError("Invalid characters detected")

        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Sanitize message field with strict length limits"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")

        v = v.strip()

        if len(v) < 10:
            raise ValueError("Message must be at least 10 characters")
        if len(v) > 1000:
            raise ValueError("Message cannot exceed 1000 characters")

        # Prevent script injection
        if "<script" in v.lower() or "javascript:" in v.lower():
            raise ValueError("Invalid content detected")

        return v


class Project(BaseModel):
    id: int
    title: str
    description: str
    technologies: List[str]
    image_url: str
    case_study_url: Optional[str] = None
    impact: str


class Testimonial(BaseModel):
    id: int
    client_name: str
    company: str
    position: str
    text: str
    rating: int
    avatar_url: Optional[str] = None


# Sample Data - Implementing Social Proof & Authority (Cialdini)
PROJECTS = [
    Project(
        id=1,
        title="LexMakesIt AI Receptionist",
        description=(
            "Saves time and missed calls. 24/7 AI phone system that "
            "handles customer inquiries, schedules appointments, and provides information so "
            "business owners can focus on their core operations, not their phones."
        ),
        technologies=["FastAPI", "Twilio", "OpenAI GPT", "RAG", "Redis", "PostgreSQL"],
        image_url="/static/images/TAWOG.jpg",
        case_study_url="/projects/ai-receptionist",
        impact=(
            "Started with a simple question: What if small businesses "
            "never missed a call? Now saves businesses 20+ hours/month and "
            "reduces operational costs."
        ),
    ),
    Project(
        id=2,
        title="DonXera Website Demo",
        description=(
            "Built for my cousin's resell store in Royal Palm Beach, Florida. "
            "Real-time inventory tracking synced with SAP ARP and Lightspeed POS. "
            "Handles 140+ SKUs with smart brand search and automated reconciliation "
            "across multiple locations at 10131 Southern Blvd, Royal Palm Beach, FL 33411."
        ),
        technologies=[
            "Python",
            "Flask",
            "SAP ARP",
            "Google Sheets API",
            "Lightspeed API",
            "PostgreSQL",
            "Docker",
        ],
        image_url="/static/images/DonXlogo.jpg",
        case_study_url="http://don-era.lexmakesit.com",
        impact=(
            "Turned a 4-hour weekly reconciliation task into a real-time automated system. "
            "No more manual counting. Instant stock visibility across all locations."
        ),
    ),
]

TESTIMONIALS = [
    Testimonial(
        id=1,
        client_name="Maria Torres",
        company="Bella Vista Salon",
        position="Owner",
        text=(
            "Alex built me an AI receptionist that actually works. "
            "I can focus on my clients instead of answering the phone all day. "
            "It's like having an extra pair of hands."
        ),
        rating=5,
        avatar_url="/static/images/client1.jpg",
    ),
    Testimonial(
        id=2,
        client_name="David Kim",
        company="Kim's HVAC Services",
        position="Operations Manager",
        text=(
            "He explained everything in plain English — no tech jargon. "
            "The AI handles our after-hours calls perfectly. Simple solution, big impact."
        ),
        rating=5,
        avatar_url="/static/images/client2.jpg",
    ),
    Testimonial(
        id=3,
        client_name="Alex Martinez",
        company="DonXEra Streetwear",
        position="Store Manager",
        text=(
            "We went from chaotic spreadsheets to a clean system that just works. "
            "Alexander walked me through every step. Real talk: this saved us hours every week."
        ),
        rating=5,
        avatar_url="/static/images/client3.jpg",
    ),
]

TOOLS_EXPERTISE = [
    {"name": "FastAPI", "category": "Framework"},
    {"name": "Python", "category": "Language"},
    {"name": "Flask", "category": "Framework"},
    {"name": "SAP ARP", "category": "Enterprise"},
    {"name": "Lua + Roblox", "category": "Game Dev"},
    {"name": "PostgreSQL", "category": "Database"},
    {"name": "Redis", "category": "Cache"},
    {"name": "RAG/Vector DB", "category": "AI/ML"},
    {"name": "OpenAI API", "category": "AI/ML"},
    {"name": "Twilio API", "category": "Communications"},
    {"name": "Google Sheets API", "category": "Integration"},
    {"name": "Lightspeed API", "category": "POS Integration"},
    {"name": "Docker", "category": "DevOps"},
    {"name": "HTML/CSS", "category": "Frontend"},
    {"name": "Bootstrap 5", "category": "UI Framework"},
]

CERTIFICATIONS = [
    "FastAPI Production Best Practices",
    "Twilio Voice & SMS Integration Specialist",
    "SAP ARP Enterprise Inventory Automation",
    "OpenAI API & RAG Systems Architecture",
    "Python Full-Stack Development",
]


# Utility Functions
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ============================================================================
# EMAIL NOTIFICATION FUNCTION
# ============================================================================


async def send_contact_email(name: str, email: str, subject: str, message: str) -> bool:
    """
    Send email notification using SendGrid Web API (bypasses port 587 block)
    Returns True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not configured - email notification skipped")
        return False

    import httpx

    try:
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        }

        # Use the verified sender email from config
        from_email = SMTP_FROM_EMAIL or SMTP_USER

        payload = {
            "personalizations": [
                {
                    "to": [{"email": CONTACT_RECIPIENT_EMAIL}],
                    "reply_to": {"email": email, "name": name},
                    "subject": f"Portfolio Contact: {subject}",
                }
            ],
            "from": {"email": from_email, "name": SMTP_FROM_NAME},
            "content": [
                {
                    "type": "text/html",
                    "value": f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;
                                border: 1px solid #ddd; border-radius: 8px;">
                        <h2 style="color: #8b5cf6; border-bottom: 2px solid #8b5cf6;
                                   padding-bottom: 10px;">
                            🔔 New Portfolio Contact Form Submission
                        </h2>

                        <div style="background-color: #f9f9f9; padding: 15px;
                                    border-radius: 5px; margin: 20px 0;">
                            <p style="margin: 5px 0;"><strong>From:</strong> {name}</p>
                            <p style="margin: 5px 0;">
                                <strong>Email:</strong> <a href="mailto:{email}">{email}</a>
                            </p>
                            <p style="margin: 5px 0;"><strong>Subject:</strong> {subject}</p>
                            <p style="margin: 5px 0;">
                                <strong>Time:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
                            </p>
                        </div>

                        <div style="background-color: #fff; padding: 15px;
                                    border-left: 4px solid #8b5cf6; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #555;">Message:</h3>
                            <p style="white-space: pre-wrap;">{message}</p>
                        </div>

                        <div style="margin-top: 20px; padding-top: 15px;
                                    border-top: 1px solid #ddd; font-size: 12px; color: #888;">
                            <p>Reply directly to the email metadata to respond to {name}.</p>
                            <p>This notification was sent from your portfolio contact form via SendGrid.</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Contact email sent successfully via SendGrid from {name} ({email})")
            return True
        else:
            logger.error(
                f"SendGrid API error: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"Unexpected error sending contact email via SendGrid: {str(e)}")
        return False


async def send_discord_notification(name: str, email: str, subject: str, message: str) -> bool:
    """Send contact form notification to Discord via webhook."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not configured - Discord notification skipped")
        return False

    import httpx

    try:
        payload = {
            "embeds": [
                {
                    "title": f"📬 New Contact: {subject}",
                    "color": 0x3B82F6,
                    "fields": [
                        {"name": "Name", "value": name, "inline": True},
                        {"name": "Email", "value": email, "inline": True},
                        {"name": "Message", "value": message[:1024]},
                    ],
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "footer": {"text": "lexmakesit.com contact form"},
                }
            ]
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            logger.info(f"Discord notification sent for contact from {name}")
            return True
        else:
            logger.error(f"Discord webhook error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error sending Discord notification: {str(e)}")
        return False


# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return FileResponse("static/index.html")


@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request):
    """Services overview.

    This URL used to be AI Receptionist plans only, which framed the whole
    practice as a single product. It now leads with what gets built for
    businesses; the receptionist keeps its own page, with its plans and
    checkout untouched, and is linked from here as one productised service.
    """
    return FileResponse("static/projects/services.html")


@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """
    Privacy policy page for Google OAuth compliance
    """
    return templates.TemplateResponse(
        request=request,
        name="privacy-policy.html",
        context={"request": request},
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service(request: Request):
    """
    Terms of Service page for Google OAuth compliance
    """
    return templates.TemplateResponse(
        request=request,
        name="terms.html",
        context={"request": request},
    )


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page."""
    return FileResponse("static/projects/about.html")


@app.get("/api/projects")
@limiter.limit("10/minute")
async def get_projects(request: Request):
    """Get all projects - Social Proof"""
    return {"projects": [p.model_dump() for p in PROJECTS]}


@app.get("/api/projects/{project_id}")
@limiter.limit("20/minute")
async def get_project(request: Request, project_id: int):
    """Get specific project details"""
    project = next((p for p in PROJECTS if p.id == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.dict()


@app.get("/api/testimonials")
@limiter.limit("10/minute")
async def get_testimonials(request: Request):
    """Get client testimonials - Social Proof & Authority"""
    return {"testimonials": [t.model_dump() for t in TESTIMONIALS]}


@app.post("/api/contact")
@limiter.limit("5/hour")
async def contact(request: Request, form_data: ContactForm):
    """
    Handle contact form submissions with email notification
    Security: Input validation, rate limiting, sanitization
    """
    try:
        # Log contact submission (sanitized)
        logger.info(f"Contact form submitted by {form_data.name[:20]}...")

        # Use default subject if not provided
        email_subject = form_data.subject or "lexmakesit email"

        # Send notifications (email + Discord) concurrently
        import asyncio
        email_sent, discord_sent = await asyncio.gather(
            send_contact_email(
                name=form_data.name,
                email=form_data.email,
                subject=email_subject,
                message=form_data.message,
            ),
            send_discord_notification(
                name=form_data.name,
                email=form_data.email,
                subject=email_subject,
                message=form_data.message,
            ),
        )

        # Log contact form submission (in production: save to database)
        contact_id = secrets.token_hex(8)
        logger.info(
            f"Contact form submitted - ID: {contact_id}, "
            f"Name: {form_data.name}, Email: {form_data.email}, "
            f"Email sent: {email_sent}, Discord sent: {discord_sent}"
        )

        # Write the enquiry down before worrying about notifications.
        # Notifications are best effort - an SMTP outage or an unset webhook
        # must never be the reason a lead disappears.
        stored = await storage.save_contact(
            public_id=contact_id,
            name=form_data.name,
            email=str(form_data.email),
            subject=email_subject,
            message=form_data.message,
            notified=bool(email_sent or discord_sent),
            source_ip=client_ip_key(request),
            user_agent=request.headers.get("user-agent", "")[:400] or None,
        )

        # Recorded is enough to promise a reply, even if every notification
        # channel is down: the message is safely on disk and retrievable.
        if stored:
            if not (email_sent or discord_sent):
                logger.warning(
                    "Contact %s stored but not notified - no channel delivered",
                    contact_id,
                )
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "message": "Thank you! I'll respond within 24 hours.",
                    "contact_id": contact_id,
                },
            )

        # Nothing stored and nothing delivered: the message exists only in a
        # log line. Saying "I'll respond within 24 hours" there is a lie that
        # costs real work, so say what actually happened.
        if not email_sent and not discord_sent:
            logger.error(
                "Contact form NOT DELIVERED - no channel configured or all failed. "
                f"ID: {contact_id}. Message is only in this log."
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "message": (
                        "Sorry — the message could not be delivered right now. "
                        "Please email as42519256@gmail.com directly so it is not lost."
                    ),
                    "contact_id": contact_id,
                },
            )

        if not email_sent:
            logger.warning(
                "Contact email failed but Discord notification succeeded - "
                f"ID: {contact_id}"
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Thank you! I'll respond within 24 hours.",
                "contact_id": contact_id,
            },
        )

    except ValueError as e:
        # Pydantic validation errors
        logger.warning(f"Contact form validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Contact form error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process your request. Please try again.",
        )


# These three rendered templates that do not exist in the image, so each
# returned a live 500. The work they pointed at now lives on the homepage,
# so they redirect there instead of erroring.

@app.get("/portfolio")
async def portfolio(request: Request):
    """The portfolio is the Featured Projects section of the homepage."""
    return RedirectResponse(url="/#work", status_code=308)


@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    """Real contact page: message form, plus direct routes."""
    return FileResponse("static/projects/contact.html")


@app.get("/blog", response_class=HTMLResponse)
async def blog(request: Request):
    """Blog index. Nothing is published yet, so this serves an honest
    placeholder in the site's own design rather than a 500 or a redirect
    that would silently drop a nav link."""
    return FileResponse("static/projects/blog.html")


@app.get("/projects/ai-receptionist", response_class=HTMLResponse)
async def ai_receptionist_project(request: Request):
    """AI Receptionist project case study with ROI calculations"""
    return templates.TemplateResponse(
        request=request, name="ai-receptionist.html", context={"request": request}
    )


# --- Project case studies -------------------------------------------
# Served as static documents the same way "/" is. The existing
# /projects/ai-receptionist route above is left untouched: it renders a
# live product page with Stripe checkout, not a case study.

_CASE_STUDIES = {
    "bakerypos": "static/projects/bakerypos.html",
    "agentop": "static/projects/agentop.html",
    "reseller": "static/projects/reseller.html",
    "contact": "static/projects/contact.html",
}


@app.get("/projects/bakerypos", response_class=HTMLResponse)
async def project_bakerypos(request: Request):
    """BakeryPOS case study."""
    return FileResponse(_CASE_STUDIES["bakerypos"])


@app.get("/projects/agentop", response_class=HTMLResponse)
async def project_agentop(request: Request):
    """Agentop case study."""
    return FileResponse(_CASE_STUDIES["agentop"])


@app.get("/projects/reseller", response_class=HTMLResponse)
async def project_reseller(request: Request):
    """Reseller App (Vendora) case study."""
    return FileResponse(_CASE_STUDIES["reseller"])


@app.post("/api/waitlist")
@limiter.limit("10/hour")
async def join_waitlist(request: Request, signup: WaitlistSignup):
    """Join the waitlist for a product that has not shipped yet."""
    result = await storage.add_waitlist(
        email=str(signup.email),
        product=signup.product,
        referrer=request.headers.get("referer", "")[:300] or None,
        source_ip=client_ip_key(request),
    )

    if result == "unavailable":
        # Better to admit the list is not being kept than to collect an
        # address that goes nowhere.
        logger.error("Waitlist signup could not be stored - storage unavailable")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "message": (
                    "Sorry — the waitlist is not accepting signups right now. "
                    "Email as42519256@gmail.com and you will be added by hand."
                )
            },
        )

    # An address already on the list is a success from the visitor's side.
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": (
                "You're on the list. You'll hear from me when it's ready."
                if result == "added"
                else "You're already on the list — nothing more to do."
            ),
            "status": result,
        },
    )


@app.get("/api/waitlist/count")
@limiter.limit("30/minute")
async def waitlist_total(request: Request, product: str = "reseller"):
    """Public count, used for social proof on the product page."""
    count = await storage.waitlist_count(product)
    if count is None:
        return JSONResponse(status_code=503, content={"count": None})
    return {"product": product, "count": count}


# --- Blog -----------------------------------------------------------
# Public reading is open. Writing requires the single admin session
# cookie; there is no registration path and no password reset, because
# there is exactly one operator.


class BlogPostIn(BaseModel):
    slug: str
    title: str
    summary: Optional[str] = None
    body: str
    published: bool = False

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", v):
            raise ValueError("Slug must be lowercase letters, numbers and hyphens")
        return v

    @field_validator("title", "body")
    @classmethod
    def validate_required_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class AdminLogin(BaseModel):
    password: str


def _admin_ok(request: Request) -> bool:
    """True when the caller holds a valid, unexpired admin session."""
    token = request.cookies.get("lex_admin")
    if not token or not ADMIN_PASSWORD_HASH:
        return False
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("role") == "admin"
    except Exception:
        return False


def _require_admin(request: Request) -> None:
    if not _admin_ok(request):
        raise HTTPException(status_code=401, detail="Not signed in")


@app.post("/api/admin/login")
@limiter.limit("5/hour")
async def admin_login(request: Request, creds: AdminLogin):
    """Sign in to the blog editor.

    Deliberately limited to five attempts an hour per client: with a single
    account and no lockout, throttling is the only thing standing between a
    guessed password and the editor.
    """
    if not ADMIN_PASSWORD_HASH:
        # No credential configured means the admin surface does not exist,
        # rather than existing with a default password.
        raise HTTPException(status_code=404, detail="Not found")

    if not verify_password(creds.password, ADMIN_PASSWORD_HASH):
        logger.warning("Failed admin login from %s", client_ip_key(request))
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = create_access_token(
        {"role": "admin"}, timedelta(hours=ADMIN_SESSION_HOURS)
    )
    response = JSONResponse(content={"message": "Signed in"})
    response.set_cookie(
        "lex_admin", token,
        max_age=ADMIN_SESSION_HOURS * 3600,
        httponly=True,          # not readable from JavaScript
        secure=PRODUCTION,      # HTTPS only in production
        samesite="strict",      # not sent on cross-site requests
        path="/",
    )
    return response


@app.post("/api/admin/logout")
async def admin_logout(request: Request):
    response = JSONResponse(content={"message": "Signed out"})
    response.delete_cookie("lex_admin", path="/")
    return response


@app.get("/api/admin/session")
async def admin_session(request: Request):
    return {"signed_in": _admin_ok(request)}


@app.get("/api/posts")
@limiter.limit("60/minute")
async def api_list_posts(request: Request):
    """Published posts, newest first. Drafts require a session."""
    return {"posts": await storage.list_posts(include_drafts=_admin_ok(request))}


@app.get("/api/posts/{slug}")
@limiter.limit("60/minute")
async def api_get_post(request: Request, slug: str):
    post = await storage.get_post(slug, include_drafts=_admin_ok(request))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.post("/api/posts")
@limiter.limit("60/hour")
async def api_save_post(request: Request, post: BlogPostIn):
    _require_admin(request)
    ok = await storage.upsert_post(
        slug=post.slug, title=post.title, summary=post.summary,
        body=post.body, published=post.published,
    )
    if not ok:
        raise HTTPException(status_code=503, detail="Could not save the post")
    return JSONResponse(status_code=201, content={"message": "Saved", "slug": post.slug})


@app.delete("/api/posts/{slug}")
@limiter.limit("30/hour")
async def api_delete_post(request: Request, slug: str):
    _require_admin(request)
    if not await storage.delete_post(slug):
        raise HTTPException(status_code=503, detail="Could not delete the post")
    return {"message": "Deleted"}


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post_page(request: Request, slug: str):
    """One post. The shell is static; the body is fetched client-side."""
    return FileResponse("static/projects/post.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not ADMIN_PASSWORD_HASH:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse("static/projects/admin.html")


@app.get("/api/health")
@limiter.limit("30/minute")
async def health_check(request: Request):
    """Health check endpoint with rate limiting"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deployment": "LexMakesIt-v1.3.0",
        "date": "2026-01-21",
        # version info for deployment verification
    }


# ============================================================================
# SEO — sitemap + robots

@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap():
    pages = [
        ("https://lexmakesit.com/", "weekly", "1.0"),
        ("https://lexmakesit.com/about", "monthly", "0.8"),
        ("https://lexmakesit.com/pricing", "monthly", "0.8"),
        ("https://lexmakesit.com/projects/ai-receptionist", "monthly", "0.7"),
        ("https://lexmakesit.com/privacy-policy", "yearly", "0.3"),
        ("https://lexmakesit.com/terms", "yearly", "0.3"),
    ]
    today = datetime.utcnow().strftime("%Y-%m-%d")
    urls = "\n".join(
        f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{pri}</priority>
  </url>"""
        for loc, freq, pri in pages
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""
    return HTMLResponse(content=xml, media_type="application/xml")


@app.get("/robots.txt")
async def robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "Sitemap: https://lexmakesit.com/sitemap.xml\n"
    )
    return HTMLResponse(content=content, media_type="text/plain")


# ============================================================================
# STRIPE PAYMENT INTEGRATION
# ============================================================================

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

# Pricing tier configuration
PRICING_TIERS = {
    "starter": {"name": "Starter", "price": 75, "minutes": 100, "price_id": "price_1Sro5E25J162lH5djEsUZnrQ"},
    "professional": {"name": "Professional", "price": 150, "minutes": 425, "price_id": "price_1Srnl925J162lH5dYtAcLBQ0"},
    "business": {"name": "Business", "price": 250, "minutes": 900, "price_id": "price_1SroYB25J162lH5dh3QPAMAL"},
}


class CheckoutRequest(BaseModel):
    tier: str
    email: EmailStr
    include_setup_fee: bool = False


@app.post("/api/stripe/create-checkout-session")
@limiter.limit("10/minute")
async def create_checkout_session(request: Request, checkout_data: CheckoutRequest):
    """Create a Stripe checkout session for subscription purchase"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")
    
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        tier = checkout_data.tier.lower()
        if tier not in PRICING_TIERS:
            raise HTTPException(status_code=400, detail="Invalid pricing tier")
        
        tier_info = PRICING_TIERS[tier]
        
        # Create Stripe checkout session
        line_item = {
            "quantity": 1,
        }
        
        # If we have a specific Price ID (configured in Stripe), use it.
        # This is required for Metered Billing to work!
        if "price_id" in tier_info and "REPLACE" not in tier_info["price_id"]:
            line_item["price"] = tier_info["price_id"]
        else:
            # Fallback: Create ad-hoc pricing (Note: Does NOT support usage metering)
            line_item["price_data"] = {
                "currency": "usd",
                "product_data": {
                    "name": f"AI Receptionist - {tier_info['name']}",
                    "description": f"{tier_info['minutes']} minutes/month included",
                },
                "unit_amount": tier_info['price'] * 100,  # Stripe uses cents
                "recurring": {"interval": "month"},
            }
            
        # Compile line items
        line_items = [line_item]
        
        # Add Setup Fee if requested (VIP Mode)
        if checkout_data.include_setup_fee:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "White Glove Setup Fee",
                        "description": "Professional Onboarding & Custom AI Prompts",
                    },
                    "unit_amount": 30000,  # $300.00
                },
                "quantity": 1,
            })

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="subscription",
            success_url="https://dashboard.lexmakesit.com/welcome?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://lexmakesit.com/projects/ai-receptionist#pricing",
            customer_email=checkout_data.email,
            metadata={
                "tier": tier,
                "email": checkout_data.email,
                "setup_fee_paid": str(checkout_data.include_setup_fee)
            },
        )
        
        logger.info(f"Checkout session created for {checkout_data.email} - tier: {tier} - setup_fee: {checkout_data.include_setup_fee}")
        return {"checkout_url": session.url, "session_id": session.id}
        
    except Exception as e:
        logger.error(f"Stripe checkout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for payment processing"""
    if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe not configured for webhooks")
        raise HTTPException(status_code=500, detail="Webhook not configured")
    
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid Stripe webhook payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid Stripe webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            customer_email = session.get("customer_email")
            tier = session.get("metadata", {}).get("tier", "starter")
            
            logger.info(f"Payment completed for {customer_email} - tier: {tier}")
            
            # Send welcome email with dashboard access
            await send_welcome_email(customer_email, tier)
            
        elif event["type"] == "customer.subscription.created":
            subscription = event["data"]["object"]
            logger.info(f"Subscription created: {subscription['id']}")
            
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            logger.info(f"Subscription cancelled: {subscription['id']}")
        
        return JSONResponse(content={"status": "success"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def send_welcome_email(email: str, tier: str) -> bool:
    """Send welcome email with dashboard access after purchase"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured - welcome email skipped")
        return False
    
    try:
        tier_info = PRICING_TIERS.get(tier, PRICING_TIERS["starter"])
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎉 Welcome to AI Receptionist - Your Account is Ready!"
        msg["From"] = SMTP_USER
        msg["To"] = email
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;
                        background: linear-gradient(135deg, #60aaff 0%, #3d84ff 100%);
                        border-radius: 16px;">
                <div style="background: white; border-radius: 12px; padding: 30px;">
                    <h1 style="color: #3d84ff; margin-bottom: 20px;">Welcome to AI Receptionist! 🎉</h1>
                    
                    <p>Thank you for choosing the <strong>{tier_info['name']}</strong> plan!</p>
                    
                    <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Your Plan Details:</h3>
                        <p><strong>Plan:</strong> {tier_info['name']}</p>
                        <p><strong>Included Minutes:</strong> {tier_info['minutes']}/month</p>
                        <p><strong>Monthly Rate:</strong> ${tier_info['price']}/month</p>
                    </div>
                    
                    <h3>Next Steps:</h3>
                    <ol>
                        <li>Access your dashboard to complete onboarding</li>
                        <li>Set up your business profile</li>
                        <li>Choose your phone number</li>
                        <li>Customize your AI receptionist</li>
                    </ol>
                    
                    <a href="https://dashboard.lexmakesit.com" 
                       style="display: inline-block; background: #3d84ff; color: white; 
                              padding: 14px 28px; text-decoration: none; border-radius: 8px;
                              font-weight: bold; margin: 20px 0;">
                        Access Your Dashboard →
                    </a>
                    
                    <p style="margin-top: 30px; color: #666; font-size: 14px;">
                        Questions? Reply to this email or visit our support page.<br>
                        - Lex Santiago, lexmakesit
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)
        
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
            timeout=10,
        )
        
        logger.info(f"Welcome email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return False


# ============================================================================
# SECURE ERROR HANDLERS (OWASP: Hide Implementation Details)
# ============================================================================


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler - no sensitive path disclosure"""
    logger.warning(f"404 error: {request.url.path}")
    return templates.TemplateResponse(
        request=request, name="404.html", context={"request": request}, status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """
    Custom 500 handler - log errors privately, show generic message
    OWASP: Never expose stack traces or implementation details
    """
    logger.error(f"Internal error: {str(exc)}", exc_info=True)

    # In production, return generic error
    if os.getenv("PRODUCTION"):
        return templates.TemplateResponse(
            request=request,
            name="500.html",
            context={"request": request},
            status_code=500,
        )

    # In development, show details (remove in production)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


@app.exception_handler(ValueError)
async def validation_error_handler(request: Request, exc: ValueError):
    """Handle validation errors securely"""
    logger.warning(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=8001,
        reload=True,
        ssl_keyfile=None,  # Add SSL cert paths in production
        ssl_certfile=None,
    )
# trigger
