'use client';

import React, { useEffect, useState, useRef } from 'react';
import {
    browseVoices, selectVoice, VoiceInfo,
    selectOpenAIVoice, openAIVoicePreviewUrl,
    OPENAI_VOICES, type OpenAIVoiceId,
} from '../lib/voiceApi';

interface VoiceBrowserProps {
    /** ElevenLabs voice ID currently active (if provider is elevenlabs) */
    currentVoiceId?: string | null;
    /** OpenAI voice name currently active (if provider is openai) */
    currentOpenAIVoice?: string | null;
    /** Which provider is currently selected: 'openai' | 'elevenlabs' */
    currentProvider?: string | null;
    onVoiceSelected?: (voiceId: string, voiceName: string) => void;
}

export default function VoiceBrowser({
    currentVoiceId,
    currentOpenAIVoice,
    currentProvider,
    onVoiceSelected,
}: VoiceBrowserProps) {
    // â”€â”€ ElevenLabs state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const [voices, setVoices] = useState<VoiceInfo[]>([]);
    const [elLoading, setElLoading] = useState(true);
    const [error, setError] = useState('');
    const [playingId, setPlayingId] = useState<string | null>(null);
    const [selecting, setSelecting] = useState<string | null>(null);
    const [successId, setSuccessId] = useState<string | null>(null);
    const [filter, setFilter] = useState<string>('all');
    const [search, setSearch] = useState('');

    // â”€â”€ OpenAI state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    // optimisticOpenAI: reflects the selection the moment the user clicks,
    // before the API round-trip finishes â€” makes the UI feel instant.
    const [optimisticOpenAI, setOptimisticOpenAI] = useState<string | null>(
        currentProvider === 'openai' ? (currentOpenAIVoice ?? null) : null
    );
    const [optimisticProvider, setOptimisticProvider] = useState<string | null>(currentProvider ?? null);
    const [oaiSelecting, setOaiSelecting] = useState<string | null>(null);
    const [oaiSuccessId, setOaiSuccessId] = useState<string | null>(null);

    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        loadVoices();
    }, []);

    // Sync optimistic state when props change (e.g. parent reloads settings)
    useEffect(() => {
        setOptimisticProvider(currentProvider ?? null);
        if (currentProvider === 'openai') {
            setOptimisticOpenAI(currentOpenAIVoice ?? null);
        }
    }, [currentProvider, currentOpenAIVoice]);

    async function loadVoices() {
        setElLoading(true);
        setError('');
        try {
            const data = await browseVoices();
            setVoices(data);
        } catch (err: unknown) {
            // browseVoices returns [] when ElevenLabs key is absent â€” this path
            // only fires on genuine network / auth failures.
            const message = err instanceof Error ? err.message : 'Failed to load voices';
            setError(message);
        } finally {
            setElLoading(false);
        }
    }

    // â”€â”€ Audio playback (ElevenLabs preview URLs / OpenAI TTS stream) â”€â”€â”€â”€â”€â”€â”€
    function playAudio(id: string, url: string) {
        if (playingId === id) {
            audioRef.current?.pause();
            audioRef.current = null;
            setPlayingId(null);
            return;
        }
        audioRef.current?.pause();
        audioRef.current = null;

        const audio = new Audio(url);
        audioRef.current = audio;
        setPlayingId(id);
        audio.play().catch(() => setPlayingId(null));
        audio.onended = () => { setPlayingId(null); audioRef.current = null; };
        audio.onerror = () => { setPlayingId(null); audioRef.current = null; };
    }

    function playElevenLabsPreview(voice: VoiceInfo) {
        if (!voice.preview_url) return;
        playAudio(voice.voice_id, voice.preview_url);
    }

    function playOpenAIPreview(voiceId: OpenAIVoiceId) {
        // The preview endpoint requires auth cookies â€” fetch as blob first
        const previewKey = `oai-${voiceId}`;
        if (playingId === previewKey) {
            audioRef.current?.pause();
            audioRef.current = null;
            setPlayingId(null);
            return;
        }
        audioRef.current?.pause();
        audioRef.current = null;
        setPlayingId(previewKey);

        fetch(openAIVoicePreviewUrl(voiceId), { credentials: 'include' })
            .then(r => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.blob();
            })
            .then(blob => {
                const url = URL.createObjectURL(blob);
                const audio = new Audio(url);
                audioRef.current = audio;
                audio.play().catch(() => setPlayingId(null));
                audio.onended = () => { setPlayingId(null); audioRef.current = null; URL.revokeObjectURL(url); };
                audio.onerror = () => { setPlayingId(null); audioRef.current = null; URL.revokeObjectURL(url); };
            })
            .catch(() => setPlayingId(null));
    }

    // Cleanup audio on unmount
    useEffect(() => {
        return () => { audioRef.current?.pause(); audioRef.current = null; };
    }, []);

    // â”€â”€ ElevenLabs voice selection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async function handleSelectElevenLabs(voice: VoiceInfo) {
        setSelecting(voice.voice_id);
        setError('');
        try {
            await selectVoice(voice.voice_id, voice.name, voice.preview_url || undefined);
            setSuccessId(voice.voice_id);
            setOptimisticProvider('elevenlabs');
            onVoiceSelected?.(voice.voice_id, voice.name);
            setTimeout(() => setSuccessId(null), 3000);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to select voice';
            setError(message);
        } finally {
            setSelecting(null);
        }
    }

    // â”€â”€ OpenAI voice selection (optimistic) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async function handleSelectOpenAI(voiceId: OpenAIVoiceId) {
        // Instantly update UI â€” don't wait for the API
        setOptimisticOpenAI(voiceId);
        setOptimisticProvider('openai');
        setOaiSelecting(voiceId);

        try {
            await selectOpenAIVoice(voiceId);
            setOaiSuccessId(voiceId);
            onVoiceSelected?.(voiceId, OPENAI_VOICES.find(v => v.id === voiceId)?.label ?? voiceId);
            setTimeout(() => setOaiSuccessId(null), 2500);
        } catch (err: unknown) {
            // Revert optimistic update on failure
            setOptimisticOpenAI(currentOpenAIVoice ?? null);
            setOptimisticProvider(currentProvider ?? null);
            const message = err instanceof Error ? err.message : 'Failed to select voice';
            setError(message);
        } finally {
            setOaiSelecting(null);
        }
    }

    // â”€â”€ Filter / search (ElevenLabs voices only) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const filteredVoices = voices.filter((v: VoiceInfo) => {
        if (filter !== 'all' && v.category.toLowerCase() !== filter) return false;
        if (search) {
            const q = search.toLowerCase();
            return (
                v.name.toLowerCase().includes(q) ||
                (Object.values(v.labels || {}) as string[]).some(l => l.toLowerCase().includes(q)) ||
                v.description?.toLowerCase().includes(q)
            );
        }
        return true;
    });

    const categories = ['all', ...Array.from(new Set(voices.map((v: VoiceInfo) => v.category.toLowerCase())))];

    // â”€â”€ Render â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    return (
        <div>
            {error && (
                <div style={{
                    background: '#f8d7da', color: '#721c24',
                    padding: '0.75rem 1rem', borderRadius: '8px',
                    marginBottom: '1rem', border: '1px solid #f5c6cb', fontSize: '0.9rem',
                }}>
                    {error}
                </div>
            )}

            {/* â”€â”€ OpenAI Voices section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
            <div style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', color: '#444', fontWeight: 600 }}>
                    OpenAI Built-in Voices
                    <span style={{
                        marginLeft: '8px', fontSize: '0.72rem', padding: '2px 8px',
                        borderRadius: '10px', background: '#e8f4fd', color: '#1a73e8',
                        fontWeight: 500, verticalAlign: 'middle',
                    }}>
                        Free â€” no quota used
                    </span>
                </h4>

                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    {OPENAI_VOICES.map(v => {
                        const isActive = optimisticProvider === 'openai' && optimisticOpenAI === v.id;
                        const isPlaying = playingId === `oai-${v.id}`;
                        const isSaving = oaiSelecting === v.id;
                        const justSaved = oaiSuccessId === v.id;

                        return (
                            <div
                                key={v.id}
                                style={{
                                    minWidth: '145px', maxWidth: '165px',
                                    padding: '0.85rem', borderRadius: '12px',
                                    border: isActive ? '2px solid #3d84ff' : '1px solid #e5e5e5',
                                    background: isActive ? '#f0f6ff' : '#fafafa',
                                    display: 'flex', flexDirection: 'column', gap: '0.4rem',
                                    position: 'relative',
                                    transition: 'border-color 0.15s, background 0.15s',
                                }}
                            >
                                {isActive && (
                                    <span style={{
                                        position: 'absolute', top: '7px', right: '7px',
                                        background: '#3d84ff', color: 'white',
                                        padding: '1px 7px', borderRadius: '10px',
                                        fontSize: '0.65rem', fontWeight: 'bold',
                                    }}>
                                        Active
                                    </span>
                                )}

                                <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{v.label}</div>
                                <div style={{ fontSize: '0.75rem', color: '#777' }}>{v.description}</div>

                                <div style={{ display: 'flex', gap: '5px', marginTop: '4px' }}>
                                    {/* Preview button */}
                                    <button
                                        type="button"
                                        title={`Preview ${v.label}`}
                                        onClick={() => playOpenAIPreview(v.id as OpenAIVoiceId)}
                                        style={{
                                            flex: 1, padding: '6px 4px',
                                            borderRadius: '7px', border: '1px solid #ddd',
                                            background: isPlaying ? '#333' : '#fff',
                                            color: isPlaying ? '#fff' : '#444',
                                            cursor: 'pointer', fontSize: '0.78rem',
                                            fontWeight: 600,
                                            transition: 'background 0.15s, color 0.15s',
                                        }}
                                    >
                                        {isPlaying ? 'â¹' : 'â–¶'}
                                    </button>

                                    {/* Select button â€” responds instantly */}
                                    <button
                                        type="button"
                                        onClick={() => !isActive && !isSaving && handleSelectOpenAI(v.id as OpenAIVoiceId)}
                                        disabled={isActive || isSaving}
                                        style={{
                                            flex: 2, padding: '6px 8px',
                                            borderRadius: '7px', border: 'none',
                                            background: justSaved ? '#28a745' : isActive ? '#c0d8ff' : 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)',
                                            color: 'white',
                                            cursor: isActive ? 'default' : 'pointer',
                                            fontSize: '0.78rem', fontWeight: 700,
                                            opacity: isSaving ? 0.8 : 1,
                                            transition: 'opacity 0.15s, background 0.15s',
                                        }}
                                    >
                                        {justSaved ? 'âœ“' : isActive ? 'Selected' : isSaving ? 'â€¦' : 'Use'}
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* â”€â”€ ElevenLabs Voices section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
            <div>
                <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', color: '#444', fontWeight: 600 }}>
                    ElevenLabs Voice Library
                    <span style={{
                        marginLeft: '8px', fontSize: '0.72rem', padding: '2px 8px',
                        borderRadius: '10px', background: '#fef3e2', color: '#b45309',
                        fontWeight: 500, verticalAlign: 'middle',
                    }}>
                        Requires ElevenLabs key
                    </span>
                </h4>

                {elLoading ? (
                    <div style={{ padding: '1.5rem', textAlign: 'center', color: '#888', fontSize: '0.9rem' }}>
                        Loading voicesâ€¦
                    </div>
                ) : voices.length === 0 ? (
                    <div style={{
                        padding: '1rem', background: '#f5f5f5', borderRadius: '8px',
                        color: '#888', fontSize: '0.85rem', textAlign: 'center',
                    }}>
                        ElevenLabs voices unavailable â€” API key not configured.
                    </div>
                ) : (
                    <>
                        {/* Search & filter */}
                        <div style={{ display: 'flex', gap: '0.6rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                            <input
                                type="text"
                                placeholder="Search voicesâ€¦"
                                value={search}
                                onChange={(e: any) => setSearch(e.target.value)}
                                style={{
                                    padding: '7px 11px', borderRadius: '8px',
                                    border: '1px solid #ddd', flex: '1',
                                    minWidth: '130px', fontSize: '0.88rem',
                                }}
                            />
                            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                {categories.map(cat => (
                                    <button
                                        key={cat}
                                        type="button"
                                        onClick={() => setFilter(cat)}
                                        style={{
                                            padding: '5px 11px', borderRadius: '14px',
                                            border: filter === cat ? '2px solid #3d84ff' : '1px solid #ddd',
                                            background: filter === cat ? '#eef4ff' : '#fff',
                                            color: filter === cat ? '#3d84ff' : '#666',
                                            fontWeight: filter === cat ? 'bold' : 'normal',
                                            cursor: 'pointer', fontSize: '0.78rem',
                                            textTransform: 'capitalize',
                                        }}
                                    >
                                        {cat}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Voice cards (horizontal scroll) */}
                        <div style={{
                            display: 'flex', gap: '0.75rem', overflowX: 'auto',
                            paddingBottom: '0.5rem', scrollbarWidth: 'thin',
                        }}>
                            {filteredVoices.length === 0 && (
                                <div style={{ padding: '1rem', color: '#888' }}>
                                    No voices found{search ? ` for "${search}"` : ''}.
                                </div>
                            )}

                            {filteredVoices.map((voice: VoiceInfo) => {
                                const isActive = optimisticProvider === 'elevenlabs' && currentVoiceId === voice.voice_id;
                                const isPlaying = playingId === voice.voice_id;
                                const isSelecting = selecting === voice.voice_id;
                                const justSelected = successId === voice.voice_id;

                                return (
                                    <div
                                        key={voice.voice_id}
                                        style={{
                                            minWidth: '190px', maxWidth: '210px',
                                            padding: '0.9rem', borderRadius: '12px',
                                            border: isActive ? '2px solid #3d84ff' : '1px solid #eee',
                                            background: isActive ? '#f0f6ff' : '#fff',
                                            flexShrink: 0, display: 'flex',
                                            flexDirection: 'column', gap: '0.45rem',
                                            position: 'relative',
                                            transition: 'border-color 0.2s, background-color 0.2s',
                                        }}
                                    >
                                        {isActive && (
                                            <span style={{
                                                position: 'absolute', top: '8px', right: '8px',
                                                background: '#3d84ff', color: 'white',
                                                padding: '2px 8px', borderRadius: '12px',
                                                fontSize: '0.68rem', fontWeight: 'bold',
                                            }}>
                                                Active
                                            </span>
                                        )}

                                        <div>
                                            <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '2px' }}>
                                                {voice.name}
                                            </div>
                                            <div style={{ fontSize: '0.73rem', color: '#888', textTransform: 'capitalize' }}>
                                                {voice.category}
                                            </div>
                                        </div>

                                        {voice.labels && Object.keys(voice.labels).length > 0 && (
                                            <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap' }}>
                                                {Object.entries(voice.labels).slice(0, 3).map(([key, val]) => (
                                                    <span key={key} style={{
                                                        fontSize: '0.68rem', padding: '2px 5px',
                                                        borderRadius: '7px', background: '#f0f0f0', color: '#555',
                                                    }}>
                                                        {val}
                                                    </span>
                                                ))}
                                            </div>
                                        )}

                                        {voice.description && (
                                            <div style={{
                                                fontSize: '0.78rem', color: '#666',
                                                overflow: 'hidden', textOverflow: 'ellipsis',
                                                display: '-webkit-box',
                                                WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                                                lineHeight: '1.3',
                                            }}>
                                                {voice.description}
                                            </div>
                                        )}

                                        <div style={{ display: 'flex', gap: '5px', marginTop: 'auto' }}>
                                            <button
                                                type="button"
                                                onClick={() => playElevenLabsPreview(voice)}
                                                disabled={!voice.preview_url}
                                                style={{
                                                    flex: 1, padding: '7px',
                                                    borderRadius: '8px', border: '1px solid #ddd',
                                                    background: isPlaying ? '#333' : '#f8f9fa',
                                                    color: isPlaying ? '#fff' : '#333',
                                                    cursor: voice.preview_url ? 'pointer' : 'not-allowed',
                                                    fontSize: '0.78rem', fontWeight: 'bold',
                                                    opacity: voice.preview_url ? 1 : 0.4,
                                                    transition: 'background 0.2s, color 0.2s',
                                                }}
                                            >
                                                {isPlaying ? 'â¹ Stop' : 'â–¶ Play'}
                                            </button>

                                            <button
                                                type="button"
                                                onClick={() => handleSelectElevenLabs(voice)}
                                                disabled={isSelecting || isActive}
                                                style={{
                                                    flex: 1, padding: '7px',
                                                    borderRadius: '8px', border: 'none',
                                                    background: justSelected ? '#28a745' : isActive ? '#ccc' : 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)',
                                                    color: 'white', cursor: isActive ? 'default' : 'pointer',
                                                    fontSize: '0.78rem', fontWeight: 'bold',
                                                    opacity: isSelecting ? 0.6 : 1,
                                                    transition: 'opacity 0.2s',
                                                }}
                                            >
                                                {justSelected ? 'âœ“' : isSelecting ? 'â€¦' : isActive ? 'Selected' : 'Use'}
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
