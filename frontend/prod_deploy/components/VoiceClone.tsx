'use client';

import React, { useState, useRef } from 'react';
import { cloneVoice, deleteClone, selectVoice, getClonePreviewUrl } from '@/lib/voiceApi';
import { API_BASE_URL } from '@/lib/config';

interface VoiceCloneProps {
    hasClone: boolean;
    cloneVoiceId?: string | null;
    cloneVoiceName?: string | null;
    currentVoiceId?: string | null;
    onCloneChanged?: () => void;
}

export default function VoiceClone({
    hasClone,
    cloneVoiceId,
    cloneVoiceName,
    currentVoiceId,
    onCloneChanged,
}: VoiceCloneProps) {
    const [uploading, setUploading] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [activating, setActivating] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [name, setName] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [playingPreview, setPlayingPreview] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    const isCloneActive = hasClone && cloneVoiceId === currentVoiceId;

    async function handleUpload() {
        if (!selectedFile || !name.trim()) {
            setError('Please enter a name and select an audio file.');
            return;
        }

        setUploading(true);
        setError('');
        setSuccess('');

        try {
            const result = await cloneVoice(name.trim(), selectedFile);
            setSuccess(`Voice "${result.voice_name}" cloned successfully!`);
            setSelectedFile(null);
            setName('');
            if (fileInputRef.current) fileInputRef.current.value = '';
            onCloneChanged?.();
        } catch (err: any) {
            setError(err.message || 'Cloning failed');
        } finally {
            setUploading(false);
        }
    }

    async function handleDelete() {
        if (!confirm('Delete your cloned voice? This cannot be undone.')) return;

        setDeleting(true);
        setError('');

        try {
            await deleteClone();
            setSuccess('Cloned voice deleted. You can create a new one.');
            onCloneChanged?.();
        } catch (err: any) {
            setError(err.message || 'Delete failed');
        } finally {
            setDeleting(false);
        }
    }

    async function handleActivate() {
        if (!cloneVoiceId || !cloneVoiceName) return;

        setActivating(true);
        setError('');

        try {
            await selectVoice(cloneVoiceId, cloneVoiceName);
            setSuccess('Your cloned voice is now active!');
            onCloneChanged?.();
        } catch (err: any) {
            setError(err.message || 'Failed to activate clone');
        } finally {
            setActivating(false);
        }
    }

    function handlePlayPreview() {
        if (playingPreview) {
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }
            setPlayingPreview(false);
            return;
        }

        const audio = new Audio(`${API_BASE_URL}/api/voice/clone/preview`);
        // Send cookies for auth
        audioRef.current = audio;
        setPlayingPreview(true);

        audio.play().catch(() => {
            setPlayingPreview(false);
            setError('Could not play preview. Try again later.');
        });
        audio.onended = () => {
            setPlayingPreview(false);
            audioRef.current = null;
        };
        audio.onerror = () => {
            setPlayingPreview(false);
            audioRef.current = null;
        };
    }

    function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (!file) return;

        // Basic validation
        const maxSize = 10 * 1024 * 1024; // 10 MB
        if (file.size > maxSize) {
            setError('File is too large. Maximum size is 10 MB.');
            return;
        }

        setSelectedFile(file);
        setError('');
    }

    return (
        <div style={{
            background: '#fafbfc', padding: '1.25rem',
            borderRadius: '12px', border: '1px solid #e8e8e8',
        }}>
            <h3 style={{
                fontSize: '1rem', margin: '0 0 0.75rem 0',
                display: 'flex', alignItems: 'center', gap: '8px'
            }}>
                <span>🎤</span> Voice Cloning
                <span style={{
                    fontSize: '0.7rem', padding: '2px 8px',
                    borderRadius: '12px', background: '#e8e8e8',
                    color: '#666', fontWeight: 'normal'
                }}>
                    1 per account
                </span>
            </h3>

            {error && (
                <div style={{
                    background: '#f8d7da', color: '#721c24',
                    padding: '0.5rem 0.75rem', borderRadius: '8px',
                    marginBottom: '0.75rem', border: '1px solid #f5c6cb',
                    fontSize: '0.85rem'
                }}>
                    {error}
                </div>
            )}

            {success && (
                <div style={{
                    background: '#d4edda', color: '#155724',
                    padding: '0.5rem 0.75rem', borderRadius: '8px',
                    marginBottom: '0.75rem', border: '1px solid #c3e6cb',
                    fontSize: '0.85rem'
                }}>
                    {success}
                </div>
            )}

            {hasClone ? (
                /* Existing clone card */
                <div style={{
                    display: 'flex', flexWrap: 'wrap',
                    gap: '0.75rem', alignItems: 'center'
                }}>
                    <div style={{ flex: '1 1 200px' }}>
                        <div style={{
                            fontWeight: 'bold', fontSize: '0.95rem',
                            marginBottom: '2px'
                        }}>
                            {cloneVoiceName || 'My Clone'}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#888' }}>
                            {isCloneActive
                                ? '✅ Currently active'
                                : 'Clone is saved — tap "Use Clone" to activate'}
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        {/* Play preview (uses TTS — costs characters) */}
                        <button
                            type="button"
                            onClick={handlePlayPreview}
                            style={{
                                padding: '8px 14px', borderRadius: '8px',
                                border: '1px solid #ddd',
                                background: playingPreview ? '#333' : '#f8f9fa',
                                color: playingPreview ? '#fff' : '#333',
                                cursor: 'pointer', fontSize: '0.8rem',
                                fontWeight: 'bold'
                            }}
                        >
                            {playingPreview ? '⏹ Stop' : '▶ Preview'}
                        </button>

                        {/* Activate clone as the voice */}
                        {!isCloneActive && (
                            <button
                                type="button"
                                onClick={handleActivate}
                                disabled={activating}
                                style={{
                                    padding: '8px 14px', borderRadius: '8px',
                                    border: 'none',
                                    background: 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)',
                                    color: 'white', cursor: 'pointer',
                                    fontSize: '0.8rem', fontWeight: 'bold',
                                    opacity: activating ? 0.6 : 1,
                                }}
                            >
                                {activating ? 'Setting...' : 'Use Clone'}
                            </button>
                        )}

                        {/* Delete clone */}
                        <button
                            type="button"
                            onClick={handleDelete}
                            disabled={deleting}
                            style={{
                                padding: '8px 14px', borderRadius: '8px',
                                border: '1px solid #f5c6cb',
                                background: '#fff5f5', color: '#c0392b',
                                cursor: 'pointer', fontSize: '0.8rem',
                                fontWeight: 'bold',
                                opacity: deleting ? 0.6 : 1,
                            }}
                        >
                            {deleting ? 'Deleting...' : '🗑 Delete'}
                        </button>
                    </div>
                </div>
            ) : (
                /* Upload form */
                <div style={{ display: 'grid', gap: '0.75rem' }}>
                    <p style={{
                        fontSize: '0.85rem', color: '#666', margin: 0
                    }}>
                        Upload a clear audio recording of your voice (30 seconds to 5 minutes).
                        The AI will learn to speak like you.
                    </p>

                    <div>
                        <label style={{
                            display: 'block', marginBottom: '4px',
                            fontWeight: 'bold', fontSize: '0.85rem'
                        }}>
                            Voice Name
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={e => setName(e.target.value)}
                            placeholder="e.g. My Voice"
                            style={{
                                width: '100%', padding: '10px',
                                borderRadius: '8px', border: '1px solid #ddd',
                                fontSize: '0.9rem'
                            }}
                        />
                    </div>

                    <div>
                        <label style={{
                            display: 'block', marginBottom: '4px',
                            fontWeight: 'bold', fontSize: '0.85rem'
                        }}>
                            Audio File
                        </label>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="audio/*"
                            onChange={handleFileChange}
                            style={{ fontSize: '0.85rem' }}
                        />
                        {selectedFile && (
                            <div style={{
                                fontSize: '0.8rem', color: '#666',
                                marginTop: '4px'
                            }}>
                                📎 {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(1)} MB)
                            </div>
                        )}
                    </div>

                    <button
                        type="button"
                        onClick={handleUpload}
                        disabled={uploading || !selectedFile || !name.trim()}
                        style={{
                            padding: '10px 20px', borderRadius: '8px',
                            border: 'none',
                            background: 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)',
                            color: 'white', fontWeight: 'bold',
                            cursor: 'pointer', fontSize: '0.9rem',
                            opacity: (uploading || !selectedFile || !name.trim()) ? 0.5 : 1,
                            maxWidth: '200px'
                        }}
                    >
                        {uploading ? '🔄 Cloning...' : '🎤 Clone My Voice'}
                    </button>
                </div>
            )}
        </div>
    );
}
