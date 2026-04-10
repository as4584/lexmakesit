import { API_BASE_URL } from './config';

export interface Business {
    id?: string;
    name?: string;
    industry?: string;
    description?: string;
    greeting_style?: string;
    business_hours?: string;
    common_services?: string;
    faqs?: { question: string; answer: string }[];
    subscription_plan?: string;
    subscription_status?: string;
    minutes_used?: number;
    minutes_limit?: number;
}

export async function safeFetch<T = unknown>(
    endpoint: string,
    options: RequestInit = {},
): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
    });

    const raw = await response.text();
    const parsed = raw ? JSON.parse(raw) : null;

    if (!response.ok) {
        if (response.status === 401) {
            if (typeof window !== 'undefined') {
                window.location.href = 'https://auth.lexmakesit.com';
            }
            throw new Error('session_expired');
        }
        const message = parsed?.detail || parsed?.message || `HTTP ${response.status}`;
        throw new Error(message);
    }

    return (parsed ?? {}) as T;
}

export async function getBusiness(): Promise<Business> {
    return safeFetch<Business>('/api/business/me');
}

export async function updateBusiness(data: Partial<Business>): Promise<Business> {
    return safeFetch<Business>('/api/business/me', {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    return safeFetch<{ message: string }>('/api/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
}

export async function redirectToGoogleOAuth(): Promise<{ url: string }> {
    const business = await getBusiness();
    const businessId = business.id || '';
    return { url: `${API_BASE_URL}/oauth/google/start?business_id=${encodeURIComponent(businessId)}` };
}
