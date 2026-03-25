'use client';

import { useState, useEffect } from 'react';
import { getBusiness, updateBusiness, redirectToGoogleOAuth, changePassword, type Business } from '@/lib/api';
import styles from '../dashboard.module.css';

export default function SettingsPage() {
    const [business, setBusiness] = useState<Business | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');
    const [error, setError] = useState('');
    const [calendarError, setCalendarError] = useState('');

    // Form fields
    const [name, setName] = useState('');
    const [industry, setIndustry] = useState('');
    const [description, setDescription] = useState('');
    const [websiteUrl, setWebsiteUrl] = useState('');
    const [learnStatus, setLearnStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [learnMessage, setLearnMessage] = useState('');
    const [greetingStyle, setGreetingStyle] = useState('professional');
    const [businessHours, setBusinessHours] = useState('');
    const [commonServices, setCommonServices] = useState('');
    const [faqs, setFaqs] = useState<{ question: string; answer: string }[]>([]);

    // Google Voice
    const [googleVoiceNumber, setGoogleVoiceNumber] = useState('');
    const [googleVoiceSaving, setGoogleVoiceSaving] = useState(false);
    const [googleVoiceStatus, setGoogleVoiceStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [googleVoiceMessage, setGoogleVoiceMessage] = useState('');

    // Security fields
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPasswords, setShowPasswords] = useState(false);
    const [passwordError, setPasswordError] = useState('');
    const [passwordSuccess, setPasswordSuccess] = useState('');
    const [changingPassword, setChangingPassword] = useState(false);

    useEffect(() => {
        async function loadData() {
            try {
                const biz = await getBusiness();
                setBusiness(biz);
                setName(biz.name || '');
                setIndustry(biz.industry || '');
                setDescription(biz.description || '');
                setGreetingStyle(biz.greeting_style || 'professional');
                setBusinessHours(biz.business_hours || '');
                setCommonServices(biz.common_services || '');
                setFaqs(biz.faqs || [{ question: '', answer: '' }]);
                setWebsiteUrl(biz.website_url || '');

                // Load Google Voice number separately
                try {
                    const gvRes = await fetch('/api/voice/google-voice', { credentials: 'include' });
                    if (gvRes.ok) {
                        const gvData = await gvRes.json();
                        setGoogleVoiceNumber(gvData.google_voice_number || '');
                    }
                } catch { /* non-fatal */ }
            } catch (err) {
                console.error('Failed to load business data:', err);
                setError('Failed to load settings');
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    const handleAddFaq = () => {
        setFaqs([...faqs, { question: '', answer: '' }]);
    };

    const handleRemoveFaq = (index: number) => {
        setFaqs(faqs.filter((_, i) => i !== index));
    };

    const handleFaqChange = (index: number, field: 'question' | 'answer', value: string) => {
        const newFaqs = [...faqs];
        newFaqs[index][field] = value;
        setFaqs(newFaqs);
    };

    const handleSaveGoogleVoice = async () => {
        setGoogleVoiceSaving(true);
        setGoogleVoiceStatus('idle');
        setGoogleVoiceMessage('');
        try {
            const res = await fetch('/api/voice/google-voice', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ google_voice_number: googleVoiceNumber || null }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to save');
            }
            setGoogleVoiceStatus('success');
            setGoogleVoiceMessage(googleVoiceNumber ? 'Number saved. Callers can now be transferred to your Google Voice.' : 'Google Voice number removed.');
        } catch (err: any) {
            setGoogleVoiceStatus('error');
            setGoogleVoiceMessage(err.message || 'Failed to save number');
        } finally {
            setGoogleVoiceSaving(false);
        }
    };

    const handleLearnWebsite = async () => {
        if (!websiteUrl) return;
        setLearnStatus('loading');
        setLearnMessage('');
        try {
            const res = await fetch('/api/business/learn-website', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ url: websiteUrl }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to learn from website');
            }
            const data = await res.json();
            setLearnStatus('success');
            setLearnMessage(data.message || 'Website learned successfully!');
        } catch (err: any) {
            setLearnStatus('error');
            setLearnMessage(err.message || 'Failed to learn from website');
        }
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setSuccessMessage('');
        setError('');

        try {
            console.log('[SETTINGS] Saving settings...');
            const result = await updateBusiness({
                name,
                industry,
                description,
                website_url: websiteUrl,
                greeting_style: greetingStyle,
                business_hours: businessHours,
                common_services: commonServices,
                faqs: faqs.filter(f => f.question && f.answer) // Filter empty entries
            });
            console.log('[SETTINGS] Save successful:', result);
            
            // Reload business data to ensure UI is in sync
            const updatedBiz = await getBusiness();
            setBusiness(updatedBiz);
            
            setSuccessMessage('Settings saved successfully!');
            setTimeout(() => setSuccessMessage(''), 3000);
        } catch (err: any) {
            console.error('[SETTINGS] Save failed:', err);
            // Display the actual backend error message
            const errorMsg = err.message || err.detail || 'Failed to save settings';
            setError(errorMsg);
        } finally {
            setSaving(false);
        }
    };

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault();
        setPasswordError('');
        setPasswordSuccess('');

        if (newPassword !== confirmPassword) {
            setPasswordError('New passwords do not match');
            return;
        }

        if (newPassword.length < 8) {
            setPasswordError('New password must be at least 8 characters');
            return;
        }

        setChangingPassword(true);
        try {
            const res = await changePassword(currentPassword, newPassword);
            setPasswordSuccess(res.message);
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (err: any) {
            setPasswordError(err.message || 'Failed to change password');
        } finally {
            setChangingPassword(false);
        }
    };

    const handleManageSubscription = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/stripe/portal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to create portal session');

            const data = await response.json();
            if (data.url) {
                window.location.href = data.url;
            }
        } catch (err) {
            console.error(err);
            alert("Could not redirect to billing portal.");
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className={styles.loadingContainer}>
                <div className={styles.loadingOrb} />
                <span>Loading Settings...</span>
            </div>
        );
    }

    return (
        <div className={styles.commandCenter}>
            <aside className={styles.sidebar}>
                <nav className={styles.sidebarNav}>
                    <a href="/dashboard" className={styles.navItem}>
                        <span className={styles.navIcon}>🏠</span>
                        <span className={styles.navLabel}>Home</span>
                    </a>
                    <a href="/dashboard/receptionists" className={styles.navItem}>
                        <span className={styles.navIcon}>📋</span>
                        <span className={styles.navLabel}>Logs</span>
                    </a>
                    <a href="/dashboard/settings" className={`${styles.navItem} ${styles.active}`}>
                        <span className={styles.navIcon}>⚙️</span>
                        <span className={styles.navLabel}>Settings</span>
                    </a>
                </nav>
            </aside>

            <main className={styles.mainContent} style={{ padding: '2rem' }}>
                <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                    <header style={{ marginBottom: '2rem' }}>
                        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Business Knowledge Base</h1>
                        <p style={{ color: '#666' }}>Teach Aria about your business. These settings directly influence how your AI receptionist responds to callers.</p>
                    </header>

                    {successMessage && (
                        <div style={{ background: '#d4edda', color: '#155724', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid #c3e6cb' }}>
                            {successMessage}
                        </div>
                    )}

                    {error && (
                        <div style={{ background: '#f8d7da', color: '#721c24', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid #f5c6cb' }}>
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSave} style={{ display: 'grid', gap: '2rem' }}>

                        {/* Section 0: Subscription (New) */}
                        <section style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', border: '1px solid #eee' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                                <div>
                                    <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span>💳</span> Subscription & Billing
                                    </h2>
                                    <p style={{ color: '#666', margin: 0 }}>
                                        Current Plan: <strong style={{ color: '#3d84ff' }}>{business?.subscription_plan || 'Loading...'}</strong>
                                        {business?.subscription_status === 'active' && <span style={{ background: '#d4edda', color: '#155724', padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem', marginLeft: '10px' }}>Active</span>}
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={handleManageSubscription}
                                    style={{
                                        padding: '10px 20px',
                                        borderRadius: '8px',
                                        background: '#f8f9fa',
                                        border: '1px solid #ddd',
                                        fontWeight: 'bold',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    <span>⚙️</span> Manage Subscription / Upgrade
                                </button>
                            </div>

                            {/* Usage Bar */}
                            <div style={{ marginTop: '1.5rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                                    <span>Monthly Minutes Used</span>
                                    <span>{business?.minutes_used || 0} / {business?.minutes_limit || 100} mins</span>
                                </div>
                                <div style={{ height: '8px', background: '#eee', borderRadius: '4px', overflow: 'hidden' }}>
                                    <div style={{
                                        height: '100%',
                                        width: `${Math.min(((business?.minutes_used || 0) / (business?.minutes_limit || 100)) * 100, 100)}%`,
                                        background: (business?.minutes_used || 0) > (business?.minutes_limit || 100) ? '#ff4444' : '#3d84ff',
                                        transition: 'width 0.3s ease'
                                    }} />
                                </div>
                                <p style={{ fontSize: '0.8rem', color: '#888', marginTop: '0.5rem' }}>
                                    {(business?.minutes_used || 0) > (business?.minutes_limit || 100)
                                        ? '⚠️ You have exceeded your plan limits. Overage charges apply.'
                                        : 'Includes inbound and outbound calls.'}
                                </p>
                            </div>

                            {/* Calendar Integration */}
                            <div style={{ marginTop: '1.5rem', borderTop: '1px solid #eee', paddingTop: '1.5rem' }}>
                                {calendarError && (
                                    <div style={{ background: '#fff3cd', color: '#856404', padding: '1rem', borderRadius: '8px', marginBottom: '1rem', border: '1px solid #ffeaa7' }}>
                                        ⚠️ {calendarError}
                                    </div>
                                )}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div>
                                        <h3 style={{ fontSize: '1rem', margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <span>📅</span> Google Calendar
                                        </h3>
                                        <p style={{ color: '#666', margin: 0, fontSize: '0.9rem' }}>
                                            {business?.google_calendar_connected
                                                ? '✅ Successfully connected to your Google Calendar.'
                                                : 'Connect your calendar so Aria can check availability and book appointments.'}
                                        </p>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={async () => {
                                            setCalendarError('');
                                            try {
                                                console.log('[CALENDAR] Attempting to connect...');
                                                await redirectToGoogleOAuth(business?.id);
                                            } catch (err: any) {
                                                console.error('[CALENDAR] Connection failed:', err);
                                                setCalendarError(err.message || 'Failed to connect Google Calendar');
                                            }
                                        }}
                                        style={{
                                            padding: '10px 20px',
                                            borderRadius: '8px',
                                            background: business?.google_calendar_connected ? '#f0f0f0' : '#4285F4',
                                            color: business?.google_calendar_connected ? '#666' : 'white',
                                            border: 'none',
                                            fontWeight: 'bold',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px'
                                        }}
                                    >
                                        <span>{business?.google_calendar_connected ? '🔄 Reconnect ' : '🔗 Connect'}</span> Google Calendar
                                    </button>
                                </div>
                            </div>
                        </section>

                        {/* Section 1: Core Business Info */}
                        <section style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', border: '1px solid #eee' }}>
                            <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span>🏢</span> Business Profile
                            </h2>
                            <div style={{ display: 'grid', gap: '1.5rem' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Business Name</label>
                                    <input value={name} onChange={(e) => setName(e.target.value)} style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }} required />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Industry</label>
                                    <input value={industry} onChange={(e) => setIndustry(e.target.value)} style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }} />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Detailed Description</label>
                                    <textarea
                                        value={description}
                                        onChange={(e) => setDescription(e.target.value)}
                                        placeholder="Describe your products, services, and what makes your business unique..."
                                        style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #ddd', minHeight: '120px' }}
                                    />
                                </div>

                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Website URL</label>
                                    <p style={{ color: '#666', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                                        Let Aria read your website so she can answer questions about your business accurately.
                                    </p>
                                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                                        <input
                                            type="url"
                                            value={websiteUrl}
                                            onChange={(e) => { setWebsiteUrl(e.target.value); setLearnStatus('idle'); }}
                                            placeholder="https://yourbusiness.com"
                                            style={{ flex: 1, minWidth: '200px', padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }}
                                        />
                                        <button
                                            type="button"
                                            onClick={handleLearnWebsite}
                                            disabled={!websiteUrl || learnStatus === 'loading'}
                                            style={{
                                                padding: '12px 20px',
                                                borderRadius: '8px',
                                                background: learnStatus === 'success' ? '#28a745' : learnStatus === 'error' ? '#dc3545' : '#3d84ff',
                                                color: 'white',
                                                border: 'none',
                                                fontWeight: 'bold',
                                                cursor: (!websiteUrl || learnStatus === 'loading') ? 'not-allowed' : 'pointer',
                                                opacity: (!websiteUrl || learnStatus === 'loading') ? 0.6 : 1,
                                                whiteSpace: 'nowrap',
                                            }}
                                        >
                                            {learnStatus === 'loading' ? 'Reading...' : learnStatus === 'success' ? 'Learned!' : learnStatus === 'error' ? 'Try Again' : 'Learn from Website'}
                                        </button>
                                    </div>
                                    {learnMessage && (
                                        <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: learnStatus === 'success' ? '#28a745' : '#dc3545' }}>
                                            {learnMessage}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </section>

                        {/* Section 2: AI Persona */}
                        <section style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', border: '1px solid #eee' }}>
                            <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span>🤖</span> AI Persona Settings
                            </h2>
                            <div style={{ display: 'grid', gap: '1.5rem' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Greeting Style</label>
                                    <select value={greetingStyle} onChange={(e) => setGreetingStyle(e.target.value)} style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }}>
                                        <option value="professional">Professional & Formal</option>
                                        <option value="friendly">Friendly & Casual</option>
                                        <option value="witty">Witty & Enthusiastic</option>
                                        <option value="concise">Concise & Direct</option>
                                    </select>
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Business Hours</label>
                                    <input value={businessHours} onChange={(e) => setBusinessHours(e.target.value)} placeholder="e.g. 9 AM - 5 PM, Mon-Fri" style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }} />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Common Services / Prices</label>
                                    <textarea value={commonServices} onChange={(e) => setCommonServices(e.target.value)} placeholder="Listing your services and general pricing helps Aria answer questions accurately." style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #ddd', minHeight: '100px' }} />
                                </div>
                            </div>
                        </section>

                        {/* Section: Google Voice / Bring Your Own Number */}
                        <section style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', border: '1px solid #eee' }}>
                            <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span>📱</span> Bring Your Own Number
                            </h2>
                            <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                                Already have a Google Voice number you want to keep? Add it here and callers can be transferred
                                to your existing number — no need to give out a new one.
                            </p>

                            {googleVoiceMessage && (
                                <div style={{
                                    background: googleVoiceStatus === 'success' ? '#d4edda' : '#f8d7da',
                                    color: googleVoiceStatus === 'success' ? '#155724' : '#721c24',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '8px',
                                    marginBottom: '1.25rem',
                                    fontSize: '0.9rem',
                                    border: `1px solid ${googleVoiceStatus === 'success' ? '#c3e6cb' : '#f5c6cb'}`
                                }}>
                                    {googleVoiceMessage}
                                </div>
                            )}

                            <div style={{ display: 'grid', gap: '1rem' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                                        Google Voice Number
                                    </label>
                                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                                        <input
                                            type="tel"
                                            value={googleVoiceNumber}
                                            onChange={(e) => { setGoogleVoiceNumber(e.target.value); setGoogleVoiceStatus('idle'); }}
                                            placeholder="(555) 867-5309"
                                            style={{ flex: 1, minWidth: '180px', padding: '12px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '1rem' }}
                                        />
                                        <button
                                            type="button"
                                            onClick={handleSaveGoogleVoice}
                                            disabled={googleVoiceSaving}
                                            style={{
                                                padding: '12px 24px',
                                                borderRadius: '8px',
                                                background: googleVoiceStatus === 'success' ? '#28a745' : '#3d84ff',
                                                color: 'white',
                                                border: 'none',
                                                fontWeight: 'bold',
                                                cursor: googleVoiceSaving ? 'not-allowed' : 'pointer',
                                                opacity: googleVoiceSaving ? 0.6 : 1,
                                                whiteSpace: 'nowrap',
                                            }}
                                        >
                                            {googleVoiceSaving ? 'Saving...' : googleVoiceStatus === 'success' ? 'Saved' : 'Save Number'}
                                        </button>
                                        {googleVoiceNumber && (
                                            <button
                                                type="button"
                                                onClick={() => { setGoogleVoiceNumber(''); setGoogleVoiceStatus('idle'); setGoogleVoiceMessage(''); }}
                                                style={{
                                                    padding: '12px 16px',
                                                    borderRadius: '8px',
                                                    background: 'none',
                                                    border: '1px solid #ddd',
                                                    color: '#999',
                                                    cursor: 'pointer',
                                                    whiteSpace: 'nowrap',
                                                }}
                                            >
                                                Remove
                                            </button>
                                        )}
                                    </div>
                                    <p style={{ color: '#999', fontSize: '0.8rem', marginTop: '0.5rem' }}>
                                        US numbers only. Enter 10 digits — we handle the formatting.
                                    </p>
                                </div>

                                {googleVoiceNumber && (
                                    <div style={{ padding: '1rem', background: '#f8f9ff', borderRadius: '12px', border: '1px solid #e0e8ff' }}>
                                        <p style={{ margin: 0, fontSize: '0.9rem', color: '#3d84ff', fontWeight: 'bold' }}>
                                            How this works
                                        </p>
                                        <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#555' }}>
                                            When a caller asks to speak with someone or the AI can&apos;t help, they&apos;ll be transferred to {googleVoiceNumber} — so you never miss a lead even if you already have a number you love.
                                        </p>
                                    </div>
                                )}
                            </div>
                        </section>

                        {/* Section 3: Security */}
                        <section style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', border: '1px solid #eee' }}>
                            <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span>🔒</span> Security & Password
                            </h2>

                            {passwordSuccess && (
                                <div style={{ background: '#d4edda', color: '#155724', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid #c3e6cb' }}>
                                    {passwordSuccess}
                                </div>
                            )}

                            {passwordError && (
                                <div style={{ background: '#f8d7da', color: '#721c24', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid #f5c6cb' }}>
                                    {passwordError}
                                </div>
                            )}

                            <div style={{ display: 'grid', gap: '1rem', maxWidth: '400px' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Current Password</label>
                                    <input
                                        type={showPasswords ? "text" : "password"}
                                        value={currentPassword}
                                        onChange={(e) => setCurrentPassword(e.target.value)}
                                        style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>New Password</label>
                                    <input
                                        type={showPasswords ? "text" : "password"}
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Confirm New Password</label>
                                    <input
                                        type={showPasswords ? "text" : "password"}
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
                                    />
                                </div>

                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <input
                                        type="checkbox"
                                        id="showPasswords"
                                        checked={showPasswords}
                                        onChange={(e) => setShowPasswords(e.target.checked)}
                                    />
                                    <label htmlFor="showPasswords" style={{ cursor: 'pointer' }}>Show passwords</label>
                                </div>

                                <button
                                    type="button"
                                    onClick={handlePasswordChange}
                                    disabled={changingPassword || !newPassword || !currentPassword}
                                    style={{
                                        marginTop: '1rem',
                                        padding: '10px 20px',
                                        borderRadius: '8px',
                                        background: '#333',
                                        color: 'white',
                                        border: 'none',
                                        fontWeight: 'bold',
                                        cursor: 'pointer',
                                        opacity: (changingPassword || !newPassword || !currentPassword) ? 0.6 : 1
                                    }}
                                >
                                    {changingPassword ? 'Updating...' : 'Update Password'}
                                </button>
                            </div>
                        </section>

                        {/* Section 4: FAQs */}
                        <section style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', border: '1px solid #eee' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                <h2 style={{ fontSize: '1.25rem', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span>❓</span> Frequently Asked Questions
                                </h2>
                                <button type="button" onClick={handleAddFaq} style={{ color: '#3d84ff', background: 'none', border: 'none', fontWeight: 'bold', cursor: 'pointer' }}>+ Add FAQ</button>
                            </div>

                            <div style={{ display: 'grid', gap: '1rem' }}>
                                {faqs.map((faq, index) => (
                                    <div key={index} style={{ padding: '1rem', border: '1px solid #eee', borderRadius: '12px', position: 'relative' }}>
                                        <button type="button" onClick={() => handleRemoveFaq(index)} style={{ position: 'absolute', top: '10px', right: '10px', color: '#ff4444', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                                        <div style={{ marginBottom: '1rem' }}>
                                            <input
                                                placeholder="Question"
                                                value={faq.question}
                                                onChange={(e) => handleFaqChange(index, 'question', e.target.value)}
                                                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #eee', fontSize: '0.9rem', fontWeight: 'bold' }}
                                            />
                                        </div>
                                        <div>
                                            <textarea
                                                placeholder="Answer"
                                                value={faq.answer}
                                                onChange={(e) => handleFaqChange(index, 'answer', e.target.value)}
                                                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #eee', fontSize: '0.9rem', minHeight: '60px' }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        <div style={{ position: 'sticky', bottom: '2rem', display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                            <button type="button" onClick={() => window.location.href = '/dashboard'} style={{ padding: '12px 24px', borderRadius: '12px', border: '1px solid #ddd', background: 'white', fontWeight: 'bold', cursor: 'pointer' }}>Cancel</button>
                            <button
                                type="submit"
                                disabled={saving}
                                style={{
                                    padding: '12px 32px',
                                    borderRadius: '12px',
                                    border: 'none',
                                    background: 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)',
                                    color: 'white',
                                    fontWeight: 'bold',
                                    cursor: 'pointer',
                                    boxShadow: '0 4px 15px rgba(61, 132, 255, 0.3)',
                                    opacity: saving ? 0.7 : 1
                                }}
                            >
                                {saving ? 'Saving...' : 'Save All Changes'}
                            </button>
                        </div>
                    </form>
                </div>
            </main>
        </div>
    );
}
