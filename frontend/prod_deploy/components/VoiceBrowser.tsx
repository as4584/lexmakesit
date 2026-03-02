'use client';

import React, { useEffect, useState, useRef } from 'react';
import { browseVoices, selectVoice, VoiceInfo } from '@/lib/voiceApi';

interface VoiceBrowserProps {
    currentVoiceId?: string | null;
    onVoiceSelected?: (voiceId: string, voiceName: string) => void;
}

export default function VoiceBrowser({ currentVoiceId, onVoiceSelected }: VoiceBrowserProps) {
    const [voices, setVoices] = useState<VoiceInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [playingId, setPlayingId] = useState<string | null>(null);
    const [selecting, setSelecting] = useState<string | null>(null);
    const [successId, setSuccessId] = useState<string | null>(null);
    const [filter, setFilter] = useState<string>('all');
    const [search, setSearch] = useState('');
    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        loadVoices();
    }, []);

    async function loadVoices() {
        setLoading(true);
        setError('');
        try {
            const data = await browseVoices();
            setVoices(data);
        } catch (err: any) {
            setError(err.message || 'Failed to load voices');
        } finally {
            setLoading(false);
        }
    }

    function playPreview(voice: VoiceInfo) {
        if (playingId === voice.voice_id) {
            // Stop
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }
            setPlayingId(null);
            return;
        }

        // Stop any current playback
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }

        if (!voice.preview_url) return;

        const audio = new Audio(voice.preview_url);
        audioRef.current = audio;
        setPlayingId(voice.voice_id);

        audio.play().catch(() => setPlayingId(null));
        audio.onended = () => {
            setPlayingId(null);
            audioRef.current = null;
        };
        audio.onerror = () => {
            setPlayingId(null);
            audioRef.current = null;
        };
    }

    async function handleSelect(voice: VoiceInfo) {
        setSelecting(voice.voice_id);
        setError('');
        try {
            await selectVoice(voice.voice_id, voice.name, voice.preview_url || undefined);
            setSuccessId(voice.voice_id);
            onVoiceSelected?.(voice.voice_id, voice.name);
            setTimeout(() => setSuccessId(null), 3000);
        } catch (err: any) {
            setError(err.message || 'Failed to select voice');
        } finally {
            setSelecting(null);
        }
    }

    // Cleanup audio on unmount
    useEffect(() => {
        return () => {
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }
        };
    }, []);

    // Filter and search
    const filteredVoices = voices.filter(v => {
        if (filter !== 'all' && v.category.toLowerCase() !== filter) return false;
        if (search) {
            const q = search.toLowerCase();
            const nameMatch = v.name.toLowerCase().includes(q);
            const labelMatch = Object.values(v.labels || {}).some(l => l.toLowerCase().includes(q));
            const descMatch = v.description?.toLowerCase().includes(q);
            return nameMatch || labelMatch || descMatch;
        }
        return true;
    });

    // Get unique categories for filter
    const categories = ['all', ...Array.from(new Set(voices.map(v => v.category.toLowerCase())))];

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#888' }}>
                <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>🎙️</div>
                Loading voices...
            </div>
        );
    }

    return (
        <div>
            {error && (
                <div style={{
                    background: '#f8d7da', color: '#721c24',
                    padding: '0.75rem 1rem', borderRadius: '8px',
                    marginBottom: '1rem', border: '1px solid #f5c6cb',
                    fontSize: '0.9rem'
                }}>
                    {error}
                </div>
            )}

            {successId && (
                <div style={{
                    background: '#d4edda', color: '#155724',
                    padding: '0.75rem 1rem', borderRadius: '8px',
                    marginBottom: '1rem', border: '1px solid #c3e6cb',
                    fontSize: '0.9rem'
                }}>
                    ✅ Voice selected successfully!
                </div>
            )}

            {/* Search & filter bar */}
            <div style={{
                display: 'flex', gap: '0.75rem', marginBottom: '1rem',
                flexWrap: 'wrap', alignItems: 'center'
            }}>
                <input
                    type="text"
                    placeholder="Search voices..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    style={{
                        padding: '8px 12px', borderRadius: '8px',
                        border: '1px solid #ddd', flex: '1',
                        minWidth: '150px', fontSize: '0.9rem'
                    }}
                />
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {categories.map(cat => (
                        <button
                            key={cat}
                            type="button"
                            onClick={() => setFilter(cat)}
                            style={{
                                padding: '6px 12px', borderRadius: '16px',
                                border: filter === cat ? '2px solid #3d84ff' : '1px solid #ddd',
                                background: filter === cat ? '#eef4ff' : '#fff',
                                color: filter === cat ? '#3d84ff' : '#666',
                                fontWeight: filter === cat ? 'bold' : 'normal',
                                cursor: 'pointer', fontSize: '0.8rem',
                                textTransform: 'capitalize'
                            }}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* Scrollable voice cards */}
            <div style={{
                display: 'flex', gap: '1rem', overflowX: 'auto',
                paddingBottom: '0.5rem',
                scrollbarWidth: 'thin',
            }}>
                {filteredVoices.length === 0 && (
                    <div style={{ padding: '1rem', color: '#888' }}>
                        No voices found{search ? ` for "${search}"` : ''}.
                    </div>
                )}

                {filteredVoices.map(voice => {
                    const isActive = currentVoiceId === voice.voice_id;
                    const isPlaying = playingId === voice.voice_id;
                    const isSelecting = selecting === voice.voice_id;
                    const justSelected = successId === voice.voice_id;

                    return (
                        <div
                            key={voice.voice_id}
                            style={{
                                minWidth: '200px', maxWidth: '220px',
                                padding: '1rem', borderRadius: '12px',
                                border: isActive ? '2px solid #3d84ff' : '1px solid #eee',
                                background: isActive ? '#f0f6ff' : '#fff',
                                flexShrink: 0, display: 'flex',
                                flexDirection: 'column', gap: '0.5rem',
                                position: 'relative',
                                transition: 'border-color 0.2s, background-color 0.2s',
                            }}
                        >
                            {/* Active badge */}
                            {isActive && (
                                <span style={{
                                    position: 'absolute', top: '8px', right: '8px',
                                    background: '#3d84ff', color: 'white',
                                    padding: '2px 8px', borderRadius: '12px',
                                    fontSize: '0.7rem', fontWeight: 'bold'
                                }}>
                                    Active
                                </span>
                            )}

                            {/* Voice name & category */}
                            <div>
                                <div style={{ fontWeight: 'bold', fontSize: '0.95rem', marginBottom: '2px' }}>
                                    {voice.name}
                                </div>
                                <div style={{
                                    fontSize: '0.75rem', color: '#888',
                                    textTransform: 'capitalize'
                                }}>
                                    {voice.category}
                                </div>
                            </div>

                            {/* Labels / tags */}
                            {voice.labels && Object.keys(voice.labels).length > 0 && (
                                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                    {Object.entries(voice.labels).slice(0, 3).map(([key, val]) => (
                                        <span key={key} style={{
                                            fontSize: '0.7rem', padding: '2px 6px',
                                            borderRadius: '8px', background: '#f0f0f0',
                                            color: '#555'
                                        }}>
                                            {val}
                                        </span>
                                    ))}
                                </div>
                            )}

                            {/* Description (truncated) */}
                            {voice.description && (
                                <div style={{
                                    fontSize: '0.8rem', color: '#666',
                                    overflow: 'hidden', textOverflow: 'ellipsis',
                                    display: '-webkit-box',
                                    WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                                    lineHeight: '1.3'
                                }}>
                                    {voice.description}
                                </div>
                            )}

                            {/* Buttons */}
                            <div style={{
                                display: 'flex', gap: '6px', marginTop: 'auto'
                            }}>
                                {/* Play preview */}
                                <button
                                    type="button"
                                    onClick={() => playPreview(voice)}
                                    disabled={!voice.preview_url}
                                    style={{
                                        flex: 1, padding: '8px',
                                        borderRadius: '8px', border: '1px solid #ddd',
                                        background: isPlaying ? '#333' : '#f8f9fa',
                                        color: isPlaying ? '#fff' : '#333',
                                        cursor: voice.preview_url ? 'pointer' : 'not-allowed',
                                        fontSize: '0.8rem', fontWeight: 'bold',
                                        opacity: voice.preview_url ? 1 : 0.4,
                                        transition: 'background 0.2s, color 0.2s',
                                    }}
                                >
                                    {isPlaying ? '⏹ Stop' : '▶ Play'}
                                </button>

                                {/* Select voice */}
                                <button
                                    type="button"
                                    onClick={() => handleSelect(voice)}
                                    disabled={isSelecting || isActive}
                                    style={{
                                        flex: 1, padding: '8px',
                                        borderRadius: '8px', border: 'none',
                                        background: justSelected ? '#28a745' : isActive ? '#ccc' : 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)',
                                        color: 'white', cursor: isActive ? 'default' : 'pointer',
                                        fontSize: '0.8rem', fontWeight: 'bold',
                                        opacity: isSelecting ? 0.6 : 1,
                                        transition: 'opacity 0.2s',
                                    }}
                                >
                                    {justSelected ? '✓ Done' : isSelecting ? '...' : isActive ? 'Selected' : 'Use'}
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
