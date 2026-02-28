/**
 * A) Central Configuration
 * 
 * SINGLE SOURCE OF TRUTH for API and auth settings.
 * Change auth mode here to switch between cookie and bearer auth globally.
 */

// API Base URL from environment
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.lexmakesit.com';

// Auth Mode: "cookie" or "bearer"
// - "cookie": Uses credentials: "include" for HttpOnly session cookies (RECOMMENDED)
// - "bearer": Uses Authorization header with JWT token stored in localStorage
export const AUTH_MODE: 'cookie' | 'bearer' =
  (process.env.NEXT_PUBLIC_AUTH_MODE as 'cookie' | 'bearer') || 'cookie';

// Request timeout in milliseconds (defensive networking)
export const REQUEST_TIMEOUT = 30000; // 30 seconds

// Retry configuration
export const MAX_RETRIES = 2;
export const RETRY_DELAY = 1000; // 1 second

// Development mode
export const IS_DEV = process.env.NODE_ENV === 'development';

// Log configuration for debugging
export function logConfig() {
  if (IS_DEV) {
    console.log('[Config] API_BASE_URL:', API_BASE_URL);
    console.log('[Config] AUTH_MODE:', AUTH_MODE);
  }
}
