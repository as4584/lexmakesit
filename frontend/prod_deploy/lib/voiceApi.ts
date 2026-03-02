/**
 * Voice Settings API functions for ElevenLabs integration.
 *
 * Provides voice browsing, selection, cloning, and usage info.
 * All calls use cookie-based auth automatically through safeFetch.
 */

import { safeFetch } from './api';
import { API_BASE_URL } from './config';

// ============================================================================
// Types
// ============================================================================

export interface VoiceInfo {
    voice_id: string;
    name: string;
    category: string;
    description: string | null;
    labels: Record<string, string>;
    preview_url: string | null;
}

export interface VoiceSettings {
    tts_provider: string;
    elevenlabs_voice_id: string | null;
    elevenlabs_voice_name: string | null;
    elevenlabs_voice_preview_url: string | null;
    custom_clone_voice_id: string | null;
    custom_clone_voice_name: string | null;
    has_clone: boolean;
}

export interface VoiceUsage {
    character_count: number;
    character_limit: number;
    voice_limit: number;
    tier: string;
}

// ============================================================================
// Voice Browsing
// ============================================================================

/**
 * Browse available voices from the ElevenLabs library.
 * Optional category filter: 'premade', 'professional', 'cloned'
 */
export async function browseVoices(category?: string): Promise<VoiceInfo[]> {
    const query = category ? `?category=${encodeURIComponent(category)}` : '';
    return safeFetch<VoiceInfo[]>(`/api/voice/browse${query}`);
}

/**
 * Get details for a single voice.
 */
export async function getVoiceDetail(voiceId: string): Promise<VoiceInfo> {
    return safeFetch<VoiceInfo>(`/api/voice/browse/${voiceId}`);
}

// ============================================================================
// Voice Selection
// ============================================================================

/**
 * Get the user's current voice settings.
 */
export async function getVoiceSettings(): Promise<VoiceSettings> {
    return safeFetch<VoiceSettings>('/api/voice/current');
}

/**
 * Select a voice (from library or clone) as the active voice.
 */
export async function selectVoice(voiceId: string, voiceName: string, previewUrl?: string): Promise<{ ok: boolean }> {
    return safeFetch<{ ok: boolean }>('/api/voice/select', {
        method: 'PUT',
        body: JSON.stringify({
            voice_id: voiceId,
            voice_name: voiceName,
            preview_url: previewUrl || null,
        }),
    });
}

// ============================================================================
// Voice Cloning
// ============================================================================

/**
 * Clone a voice by uploading an audio file.
 * Limit: 1 clone per account. Delete existing clone first if needed.
 *
 * NOTE: Uses FormData (not JSON) — we bypass safeFetch for this endpoint.
 */
export async function cloneVoice(name: string, audioFile: File): Promise<{ ok: boolean; voice_id: string; voice_name: string; preview_url?: string }> {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('audio_file', audioFile);

    const response = await fetch(`${API_BASE_URL}/api/voice/clone`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
    });

    if (!response.ok) {
        const errText = await response.text();
        let errMsg = `HTTP ${response.status}`;
        try {
            const errJson = JSON.parse(errText);
            errMsg = errJson.detail || errJson.message || errMsg;
        } catch { }
        throw new Error(errMsg);
    }

    return response.json();
}

/**
 * Delete the user's cloned voice.
 */
export async function deleteClone(): Promise<{ ok: boolean; deleted_voice_id: string }> {
    return safeFetch<{ ok: boolean; deleted_voice_id: string }>('/api/voice/clone', {
        method: 'DELETE',
    });
}

/**
 * Get a TTS preview URL for the user's cloned voice.
 * Returns raw audio/mpeg bytes. Use with an <audio> element.
 */
export function getClonePreviewUrl(): string {
    return `${API_BASE_URL}/api/voice/clone/preview`;
}

// ============================================================================
// Usage
// ============================================================================

/**
 * Get ElevenLabs character usage / quota info.
 */
export async function getVoiceUsage(): Promise<VoiceUsage> {
    return safeFetch<VoiceUsage>('/api/voice/usage');
}
