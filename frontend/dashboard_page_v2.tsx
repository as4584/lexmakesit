'use client';

import { useEffect, useState } from 'react';
import { me, getBusiness, getRecentCalls, type User, type Business } from '../../lib/api';
import styles from './dashboard.module.css';

export default function DashboardPage() {
    const [user, setUser] = useState<User | null>(null);
    const [business, setBusiness] = useState<Business | null>(null);
    const [recentCalls, setRecentCalls] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [aiActive, setAiActive] = useState(true);
    const [showToast, setShowToast] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date());
    const [transcriptLines] = useState<{ speaker: 'caller' | 'ai', text: string }[]>([
        { speaker: 'ai', text: 'Thank you for calling! How can I help you today?' },
        { speaker: 'caller', text: 'I\'d like to schedule an appointment for next Tuesday.' },
        { speaker: 'ai', text: 'I\'d be happy to help. Let me check availability for next Tuesday...' }
    ]);

    useEffect(() => {
        async function loadData() {
            try {
                const [userData, businessData, callsData] = await Promise.all([
                    me(),
                    getBusiness().catch((err: Error) => {
                        console.warn('Real business data not found, using demo state:', err.message);
                        return null;
                    }),
                    getRecentCalls().catch(() => [])
                ]);

                setUser(userData);
                setBusiness(businessData);
                setRecentCalls(callsData);

                // If no business, redirect to onboarding if it's really missing
                if (!businessData && !loading) {
                    // router.push('/app/onboarding'); // Auto redirect if you want
                }
            } catch (error) {
                console.error('Failed to load dashboard data:', error);
            } finally {
                setLoading(false);
            }
        }
        loadData();

        // Update current time every second
        const timeInterval = setInterval(() => {
            setCurrentTime(new Date());
        }, 1000);

        // Show demo notification after 2 seconds
        setTimeout(() => setShowToast(true), 2000);

        return () => clearInterval(timeInterval);
    }, []);

    // Helper to format time based on business timezone
    const formatTime = (date: Date) => {
        const options: Intl.DateTimeFormatOptions = {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZone: business?.timezone || undefined
        };
        try {
            return date.toLocaleTimeString('en-US', options);
        } catch (e) {
            return date.toLocaleTimeString('en-US');
        }
    };

    const formatDate = (date: Date) => {
        const options: Intl.DateTimeFormatOptions = {
            month: 'long',
            year: 'numeric',
            timeZone: business?.timezone || undefined
        };
        try {
            return date.toLocaleDateString('en-US', options);
        } catch (e) {
            return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        }
    };

    if (loading) {
        return (
            <div className={styles.loadingContainer}>
                <div className={styles.loadingOrb} />
                <span>Synchronizing Systems...</span>
            </div>
        );
    }

    const hasBusiness = business != null;
    const hasPhoneNumber = business?.phone_number != null;

    return (
        <div className={styles.commandCenter}>
            {/* Left Sidebar */}
            <aside className={styles.sidebar}>
                <nav className={styles.sidebarNav}>
                    <a href="/app" className={`${styles.navItem} ${styles.active}`}>
                        <span className={styles.navIcon}>🏠</span>
                        <span className={styles.navLabel}>Home</span>
                    </a>
                    <a href="/app/receptionists" className={styles.navItem}>
                        <span className={styles.navIcon}>📋</span>
                        <span className={styles.navLabel}>Logs</span>
                    </a>
                    <a href="/app/settings" className={styles.navItem}>
                        <span className={styles.navIcon}>⚙️</span>
                        <span className={styles.navLabel}>Settings</span>
                    </a>
                </nav>
            </aside>

            {/* Main Content */}
            <main className={styles.mainContent}>
                {!hasBusiness && (
                    <section className={styles.onboardingAlert} style={{
                        background: 'linear-gradient(135deg, #fff5f5 0%, #fff 100%)',
                        border: '2px dashed #feb2b2',
                        borderRadius: '24px',
                        padding: '2rem',
                        marginBottom: '2rem',
                        textAlign: 'center'
                    }}>
                        <h2 style={{ color: '#c53030', marginBottom: '1rem' }}>Finish Setup 🚀</h2>
                        <p style={{ color: '#718096', marginBottom: '1.5rem' }}>
                            You haven't completed your business profile yet. Complete onboarding to activate your AI receptionist.
                        </p>
                        <a href="/app/onboarding" className={styles.ctaButton} style={{
                            padding: '0.8rem 2rem',
                            background: '#3182ce',
                            color: 'white',
                            borderRadius: '12px',
                            textDecoration: 'none',
                            fontWeight: 'bold',
                            display: 'inline-block'
                        }}>
                            Complete Onboarding
                        </a>
                    </section>
                )}

                {/* AI Status Card */}
                <section className={styles.aiStatusCard}>
                    <h2 className={styles.cardTitle}>AI Receptionist Status</h2>
                    <div className={styles.aiStatusContent}>
                        <div className={`${styles.statusOrb} ${aiActive && hasPhoneNumber ? styles.active : styles.inactive}`}>
                            <div className={styles.orbInner} />
                        </div>
                        <div className={styles.statusInfo}>
                            <h3>{business?.name || 'New Account'}</h3>
                            <span className={styles.statusText}>{aiActive && hasPhoneNumber ? 'Active' : 'Account Incomplete'}</span>
                        </div>
                        <label className={styles.toggleWrapper}>
                            <input
                                type="checkbox"
                                checked={aiActive && hasPhoneNumber}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAiActive(e.target.checked)}
                                className={styles.toggleInput}
                                disabled={!hasPhoneNumber}
                            />
                            <span className={styles.toggleSlider}>
                                <span className={styles.toggleKnob} />
                            </span>
                            <span className={styles.toggleLabel}>{aiActive && hasPhoneNumber ? 'ON' : 'OFF'}</span>
                        </label>
                    </div>
                    {!hasPhoneNumber && hasBusiness && (
                        <div className={styles.emptyStateInline}>
                            <p>⚠️ Phone number required to activate AI receptionist</p>
                            <a href="/app/settings" className={styles.ctaLink}>Configure Phone Number →</a>
                        </div>
                    )}
                </section>

                {hasPhoneNumber ? (
                    <>
                        {/* Live Call Feed */}
                        <section className={styles.recentLogsCard}>
                            <h3>Live Call Stream</h3>
                            <div className={styles.logsList}>
                                {recentCalls.length === 0 ? (
                                    <div className={styles.emptyState}>
                                        <p>Listening for incoming calls...</p>
                                    </div>
                                ) : (
                                    recentCalls.slice(0, 3).map((log: any, i: number) => (
                                        <div key={i} className={styles.logItem}>
                                            <span className={styles.logName}>{log.from_number}</span>
                                            <div className={styles.logTags}>
                                                <span className={`${styles.chip} ${log.status === 'in-progress' ? styles.booked : ''}`}>
                                                    {log.status === 'in-progress' ? '● In Call' : 'Completed'}
                                                </span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </section>
                    </>
                ) : (
                    <section className={styles.emptyStateCard}>
                        <div className={styles.emptyState}>
                            <span className={styles.emptyIcon}>📞</span>
                            <h3>Waiting for Numbers</h3>
                            <p>Once you choose a number in onboarding, your call feed will appear here.</p>
                        </div>
                    </section>
                )}
            </main>

            {/* Right Column */}
            <aside className={styles.rightColumn}>
                {/* Live Transcript */}
                <section className={styles.transcriptCard}>
                    <h3>Live Transcript</h3>
                    <div className={styles.transcriptContent} style={{ minHeight: '150px' }}>
                        <div className={styles.speakerChip} style={{ background: '#4A90E2', fontSize: '0.7rem' }}>Caller: Blue</div>
                        <div className={styles.speakerChip} style={{ background: '#7FFF00', color: '#000', fontSize: '0.7rem' }}>AI: Green</div>
                        <div className={styles.transcriptText} style={{ marginTop: '1rem' }}>
                            {transcriptLines.map((line, i) => (
                                <p key={i} style={{
                                    color: line.speaker === 'ai' ? '#7FFF00' : '#4A90E2',
                                    marginBottom: '0.5rem',
                                    fontSize: '0.85rem',
                                    lineHeight: '1.4'
                                }}>
                                    <strong>{line.speaker === 'ai' ? 'AI: ' : 'Caller: '}</strong>
                                    {line.text}
                                </p>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Schedule/Booking with TZ-AWARE TIME */}
                <section className={styles.scheduleCard}>
                    <h3>Business Time</h3>
                    <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
                        <div style={{ fontSize: '0.8rem', color: '#718096', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {formatDate(currentTime)}
                        </div>
                        <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#3d84ff', margin: '0.2rem 0' }}>
                            {formatTime(currentTime)}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#a0aec0' }}>
                            {business?.timezone || 'Local Browser Time'}
                        </div>
                    </div>

                    <div className={styles.miniCalendar}>
                        <div className={styles.calendarHeader}>
                            <span>S</span><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span>
                        </div>
                        <div className={styles.calendarDays}>
                            {(() => {
                                const today = currentTime.getDate();
                                const firstDay = new Date(currentTime.getFullYear(), currentTime.getMonth(), 1).getDay();
                                const daysInMonth = new Date(currentTime.getFullYear(), currentTime.getMonth() + 1, 0).getDate();
                                const days = [];
                                for (let i = 0; i < firstDay; i++) {
                                    days.push(<span key={`empty-${i}`} style={{ opacity: 0 }}>0</span>);
                                }
                                for (let i = 1; i <= daysInMonth; i++) {
                                    days.push(
                                        <span key={i} className={i === today ? styles.today : ''} style={{
                                            background: i === today ? 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)' : 'transparent',
                                            color: i === today ? 'white' : 'inherit',
                                            boxShadow: i === today ? '0 2px 5px rgba(61, 132, 255, 0.4)' : 'none'
                                        }}>{i}</span>
                                    );
                                }
                                return days;
                            })()}
                        </div>
                    </div>
                </section>

                {/* System Health */}
                <section className={styles.healthCard}>
                    <h3>System Status</h3>
                    <div className={styles.healthGrid}>
                        <div className={styles.healthItem}>
                            <div className={`${styles.healthOrb} ${hasPhoneNumber ? styles.connected : styles.inactive}`} />
                            <span>Phone</span>
                        </div>
                        <div className={styles.healthItem}>
                            <div className={`${styles.healthOrb} ${styles.healthy}`} />
                            <span>AI Core</span>
                        </div>
                        <div className={styles.healthItem}>
                            <div className={`${styles.healthOrb} ${business?.google_calendar_connected ? styles.synced : styles.inactive}`} />
                            <span>Calendar</span>
                        </div>
                    </div>
                </section>
            </aside>
        </div>
    );
}
