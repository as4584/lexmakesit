/**
 * C) Safe API Client with Defensive Networking
 * 
 * Features:
 * - Automatic timeout (no hanging requests)
 * - Endpoint fallback (tries multiple URLs if 404)
 * - Auth mode switching (cookie vs bearer)
 * - Graceful error handling
 * - TypeScript types for safety
 * - No infinite loops
 */

import { API_BASE_URL, AUTH_MODE, REQUEST_TIMEOUT, IS_DEV } from './config';
import { ENDPOINTS, getEndpointFallbacks } from './endpoints';

// ============================================================================
// Types
// ============================================================================

export interface User {
    id: string;
    email: string;
    full_name?: string;
    created_at?: string;
}

export interface Receptionist {
    id: string;
    name: string;
    business_name?: string;
    greeting_message?: string;
    business_hours?: string;
    personality?: string;
    business_info?: string;
    phone_number?: string;
    google_calendar_connected?: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface ApiError {
    message: string;
    status?: number;
    code?: string;
}

// ============================================================================
// Core Fetch with Timeout
// ============================================================================

/**
 * Fetch with automatic timeout to prevent hanging requests
 */
async function fetchWithTimeout(
    url: string,
    options: RequestInit = {},
    timeout: number = REQUEST_TIMEOUT
): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error instanceof Error && error.name === 'AbortError') {
            throw new Error(`Request timeout after ${timeout}ms`);
        }
        throw error;
    }
}

// ============================================================================
// Auth Token Management
// ============================================================================
// NOTE: With cookie-based auth, tokens are stored in HttpOnly cookies by the backend.
// We don't store tokens in localStorage anymore for security (XSS protection).
// Business ID is still stored in localStorage for OAuth flow convenience.

const BUSINESS_ID_KEY = 'business_id';

export function getBusinessId(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(BUSINESS_ID_KEY);
}

export function setBusinessId(id: string): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(BUSINESS_ID_KEY, id);
}

export function clearBusinessId(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(BUSINESS_ID_KEY);
}

// ============================================================================
// Safe Fetch with Fallbacks
// ============================================================================

/**
 * Safe fetch that:
 * 1. Tries multiple endpoint fallbacks if 404
 * 2. Adds auth (cookie or bearer) automatically
 * 3. Has timeout protection
 * 4. Parses JSON safely
 * 5. Provides clear error messages
 */
export async function safeFetch<T = any>(
    endpointOrFallbacks: string | string[],
    options: RequestInit = {}
): Promise<T> {
    const fallbacks = getEndpointFallbacks(endpointOrFallbacks);

    // Prepare headers
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Prepare fetch options with cookie credentials
    // This sends HttpOnly cookies automatically with every request
    const fetchOptions: RequestInit = {
        ...options,
        headers,
        credentials: 'include',  // Always include cookies for auth
    };

    let lastError: Error | null = null;

    // Try each fallback URL in order
    for (let i = 0; i < fallbacks.length; i++) {
        const endpoint = fallbacks[i];
        const url = `${API_BASE_URL}${endpoint}`;

        try {
            if (IS_DEV) {
                console.log(`[API] Trying ${options.method || 'GET'} ${url}`);
            }

            const response = await fetchWithTimeout(url, fetchOptions);

            // If 404 and we have more fallbacks, try next
            if (response.status === 404 && i < fallbacks.length - 1) {
                if (IS_DEV) {
                    console.log(`[API] 404 on ${url}, trying next fallback...`);
                }
                continue;
            }

            // Handle non-OK responses
            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

                try {
                    const errorJson = JSON.parse(errorText);
                    errorMessage = errorJson.message || errorJson.detail || errorMessage;
                } catch {
                    // If not JSON, use text
                    if (errorText) errorMessage = errorText;
                }

                throw Object.assign(new Error(errorMessage), {
                    status: response.status,
                    code: response.statusText,
                } as ApiError);
            }

            // Parse JSON response
            const text = await response.text();
            if (!text) return {} as T;

            try {
                return JSON.parse(text) as T;
            } catch (parseError) {
                if (IS_DEV) {
                    console.error('[API] JSON parse error:', parseError);
                }
                throw new Error('Invalid JSON response from server');
            }

        } catch (error) {
            lastError = error as Error;

            // If it's a 404 and we have more fallbacks, continue
            if ((error as ApiError).status === 404 && i < fallbacks.length - 1) {
                continue;
            }

            // If it's not a 404, or we're on the last fallback, throw
            if (i === fallbacks.length - 1) {
                throw error;
            }
        }
    }

    // If we get here, all fallbacks failed
    throw lastError || new Error('All endpoint fallbacks failed');
}

// ============================================================================
// Authentication API
// ============================================================================

export interface SignupData {
    email: string;
    password: string;
    full_name?: string;
}

export interface LoginData {
    email: string;
    password: string;
}

export interface AuthResponse {
    user: User;
    token?: string; // For bearer mode
}

/**
 * Sign up a new user
 */
export async function signup(data: SignupData): Promise<AuthResponse> {
    const response = await safeFetch<AuthResponse>(ENDPOINTS.auth.signup, {
        method: 'POST',
        body: JSON.stringify(data),
    });

    // Cookie-based auth: Backend sets HttpOnly cookie automatically
    // No need to store tokens in localStorage

    return response;
}

/**
 * Log in existing user
 */
export async function login(data: LoginData): Promise<AuthResponse> {
    const response = await safeFetch<AuthResponse>(ENDPOINTS.auth.login, {
        method: 'POST',
        body: JSON.stringify(data),
    });

    // Cookie-based auth: Backend sets HttpOnly cookie automatically
    // No need to store tokens in localStorage

    return response;
}

/**
 * Get current user (for auth check)
 */
export async function me(): Promise<User> {
    return safeFetch<User>(ENDPOINTS.auth.me);
}

/**
 * Log out current user
 */
export async function logout(): Promise<void> {
    try {
        await safeFetch(ENDPOINTS.auth.logout, {
            method: 'POST',
        });
    } finally {
        // Cookie-based auth: Backend clears HttpOnly cookie
        // Clear any local storage (business_id, etc.)
        clearBusinessId();
    }
}

// ============================================================================
// Receptionist API
// ============================================================================

export interface CreateReceptionistData {
    name: string;
    business_name?: string;
    greeting_message?: string;
    business_hours?: string;
    personality?: string;
    business_info?: string;
}

export interface UpdateReceptionistData extends Partial<CreateReceptionistData> { }

/**
 * List all receptionists for current user
 */
export async function listReceptionists(): Promise<Receptionist[]> {
    return safeFetch<Receptionist[]>(ENDPOINTS.receptionists.list);
}

/**
 * Create a new receptionist
 */
export async function createReceptionist(data: CreateReceptionistData): Promise<Receptionist> {
    return safeFetch<Receptionist>(ENDPOINTS.receptionists.create, {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

/**
 * Get a specific receptionist
 */
export async function getReceptionist(id: string): Promise<Receptionist> {
    return safeFetch<Receptionist>(ENDPOINTS.receptionists.get(id));
}

/**
 * Update a receptionist
 */
export async function updateReceptionist(id: string, data: UpdateReceptionistData): Promise<Receptionist> {
    return safeFetch<Receptionist>(ENDPOINTS.receptionists.update(id), {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

/**
 * Delete a receptionist
 */
export async function deleteReceptionist(id: string): Promise<void> {
    await safeFetch(ENDPOINTS.receptionists.delete(id), {
        method: 'DELETE',
    });
}

// ============================================================================
// Business API (for onboarding)
// ============================================================================

export interface Business {
    id: string;
    name: string;
    phone_number?: string;
    timezone?: string;
    business_hours?: string;
    greeting_message?: string;
    personality?: string;
    business_info?: string;
    google_calendar_connected?: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface CreateBusinessData {
    name: string;
    phone_number?: string;
    timezone?: string;
}

export interface UpdateBusinessData {
    business_hours?: string;
    greeting_message?: string;
    personality?: string;
    business_info?: string;
}

/**
 * Create a new business (onboarding)
 * STUB: Update endpoint path when backend is ready
 */
export async function createBusiness(data: CreateBusinessData): Promise<Business> {
    const response = await safeFetch<Business>(ENDPOINTS.business.create, {
        method: 'POST',
        body: JSON.stringify(data),
    });

    // Store business ID for later use
    if (response.id) {
        setBusinessId(response.id);
    }

    return response;
}

/**
 * Get current user's business
 */
export async function getBusiness(): Promise<Business> {
    return safeFetch<Business>('/api/business/me');
}

/**
 * Update business settings
 */
export async function updateBusiness(data: UpdateBusinessData): Promise<Business> {
    return safeFetch<Business>('/api/business/me', {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

/**
 * Get recent calls for current business
 */
export async function getRecentCalls(): Promise<any[]> {
    return safeFetch<any[]>('/api/business/calls');
}

// ============================================================================
// Twilio API
// ============================================================================

/**
 * Get available Twilio numbers for onboarding
 */
export async function getAvailableNumbers(): Promise<{ phoneNumber: string, friendlyName: string }[]> {
    // Note: Adjust prefix /twilio if needed. Current backend has router.get("/available-numbers") 
    // prefixed with /twilio in app.include_router(twilio_router, prefix="/twilio")
    return safeFetch<{ phoneNumber: string, friendlyName: string }[]>('/twilio/available-numbers');
}

/**
 * Get user's assigned numbers
 */
export async function getMyNumbers(): Promise<any[]> {
    return safeFetch<any[]>('/twilio/my-numbers');
}


// ============================================================================
// OAuth API
// ============================================================================

export interface OAuthStartResponse {
    url: string; // URL to redirect to for OAuth
}

export interface OAuthStatusResponse {
    connected: boolean;
    email?: string;
    calendar_id?: string;
}

/**
 * Start Google OAuth flow
 * Redirects browser to Google OAuth with business_id
 */
export function redirectToGoogleOAuth(businessId?: string): void {
    const bid = businessId || getBusinessId();
    if (!bid) {
        throw new Error('Business ID required for OAuth');
    }

    // Direct browser redirect to backend OAuth endpoint
    const url = `${API_BASE_URL}/oauth/google/start?business_id=${bid}`;
    window.location.href = url;
}

/**
 * Get Google OAuth URL
 */
export async function getGoogleOAuthUrl(businessId?: string): Promise<OAuthStartResponse> {
    const bid = businessId || getBusinessId();
    if (!bid) {
        throw new Error('Business ID required for OAuth');
    }
    return { url: `${API_BASE_URL}/oauth/google/start?business_id=${bid}` };
}

// Aliases for compatibility with some pages
export const oauthStart = getGoogleOAuthUrl;
export const oauthStatus = getOAuthStatus;

/**
 * Get OAuth connection status for a business
 */
export async function getOAuthStatus(businessId?: string): Promise<OAuthStatusResponse> {
    const bid = businessId || getBusinessId();
    if (!bid) {
        throw new Error('Business ID required to check OAuth status');
    }

    return safeFetch<OAuthStatusResponse>(
        `${ENDPOINTS.oauth.status}?business_id=${bid}`
    );
}

// ============================================================================
// Utility: Check if user is authenticated
// ============================================================================

/**
 * Check if user is authenticated (doesn't throw on error)
 */
export async function isAuthenticated(): Promise<boolean> {
    try {
        await me();
        return true;
    } catch {
        return false;
    }
}

