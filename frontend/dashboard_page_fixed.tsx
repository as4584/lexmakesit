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

    if (loading) {
        return (
            <div className={styles.loadingContainer}>
                <div className={styles.loadingOrb} />
                <span>Loading Command Center...</span>
            </div>
        );
    }

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
                {/* AI Status Card */}
                <section className={styles.aiStatusCard}>
                    <h2 className={styles.cardTitle}>AI Receptionist Status</h2>
                    <div className={styles.aiStatusContent}>
                        <div className={`${styles.statusOrb} ${aiActive ? styles.active : styles.inactive}`}>
                            <div className={styles.orbInner} />
                        </div>
                        <div className={styles.statusInfo}>
                            <h3>{business?.name || 'My Business'}</h3>
                            <span className={styles.statusText}>{aiActive ? 'Active' : 'Inactive'}</span>
                        </div>
                        <label className={styles.toggleWrapper}>
                            <input
                                type="checkbox"
                                checked={aiActive}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAiActive(e.target.checked)}
                                className={styles.toggleInput}
                                disabled={!hasPhoneNumber}
                            />
                            <span className={styles.toggleSlider}>
                                <span className={styles.toggleKnob} />
                            </span>
                            <span className={styles.toggleLabel}>{aiActive ? 'ON' : 'OFF'}</span>
                        </label>
                    </div>
                    {!hasPhoneNumber && (
                        <div className={styles.emptyStateInline}>
                            <p>⚠️ Phone number required to activate AI receptionist</p>
                            <a href="/app/settings" className={styles.ctaLink}>Configure Phone Number →</a>
                        </div>
                    )}
                </section>

                {hasPhoneNumber ? (
                    <>
                        {recentCalls.length > 0 && recentCalls[0]?.status === 'in-progress' && (
                            <section className={styles.liveCallStrip}>
                                <div className={styles.liveCallHeader}>
                                    <span className={styles.liveIndicator}>●</span>
                                    <span>Live Call Now Playing</span>
                                </div>
                                <div className={styles.liveCallInfo}>
                                    <div className={styles.callerInfo}>
                                        <strong>Caller: {recentCalls[0].from_number}</strong>
                                        <span>{Math.floor(recentCalls[0].duration / 60)}:{(recentCalls[0].duration % 60).toString().padStart(2, '0')} | {recentCalls[0].status}</span>
                                    </div>
                                    <div className={styles.callActions}>
                                        <button className={styles.actionBtn}>Mute</button>
                                        <button className={styles.actionBtn}>Whisper</button>
                                        <button className={styles.actionBtn}>Transfer</button>
                                        <button className={`${styles.actionBtn} ${styles.endBtn}`}>End</button>
                                    </div>
                                </div>
                            </section>
                        )}

                        <section className={styles.callQueueCard}>
                            <div className={styles.queueHeader}>
                                <div className={styles.queueOrb}>
                                    <span>{recentCalls.filter((c: any) => c.status === 'in-progress').length}</span>
                                </div>
                                <div>
                                    <h3>Active Calls</h3>
                                    <span className={styles.queueSubtext}>
                                        {recentCalls.filter((c: any) => c.status === 'in-progress').length > 0
                                            ? `Current: ${recentCalls.filter((c: any) => c.status === 'in-progress').map((c: any) => c.from_number).join(', ')}`
                                            : 'No calls in progress'}
                                    </span>
                                </div>
                            </div>
                            <div className={styles.queueList}>
                                {recentCalls.filter((c: any) => c.status === 'in-progress').map((caller: any, i: number) => (
                                    <div key={i} className={styles.queueItem}>
                                        <span className={styles.queueChip}>Live</span>
                                    </div>
                                ))}
                            </div>
                        </section>

                        <section className={styles.recentLogsCard}>
                            <h3>Recent Call Logs</h3>
                            {recentCalls.length === 0 ? (
                                <div className={styles.emptyState}>
                                    <span className={styles.emptyIcon}>📞</span>
                                    <h4>No Calls Yet</h4>
                                    <p>Once your AI receptionist receives calls, they will appear here</p>
                                </div>
                            ) : (
                                <div className={styles.logsList}>
                                    {recentCalls.slice(0, 5).map((log: any, i: number) => (
                                        <div key={i} className={styles.logItem}>
                                            <span className={styles.logName}>{log.from_number}</span>
                                            <div className={styles.logTags}>
                                                <span className={`${styles.chip} ${log.appointment_booked ? styles.booked : ''}`}>
                                                    {log.appointment_booked ? '✓ Booked' : log.intent || 'Call'}
                                                </span>
                                                <span className={styles.chip}>{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>
                    </>
                ) : (
                    <section className={styles.emptyStateCard}>
                        <div className={styles.emptyState}>
                            <span className={styles.emptyIcon}>📱</span>
                            <h3>Phone Number Required</h3>
                            <p>Set up your business phone number to start receiving AI-powered calls</p>
                            <a href="/app/settings" className={styles.ctaButton}>
                                Configure Phone Number
                            </a>
                        </div>
                    </section>
                )}
            </main>

            {/* Right Column */}
            <aside className={styles.rightColumn}>
                {/* Live Transcript */}
                <section className={styles.transcriptCard}>
                    <h3>Live Transcript</h3>
                    <div className={styles.transcriptContent}>
                        <div className={styles.speakerChip} style={{ background: '#4A90E2' }}>Caller: Blue</div>
                        <div className={styles.speakerChip} style={{ background: '#7FFF00', color: '#000' }}>AI: Green</div>
                        <div className={styles.transcriptText}>
                            {transcriptLines.map((line, i) => (
                                <p key={i} style={{
                                    color: line.speaker === 'ai' ? '#7FFF00' : '#4A90E2',
                                    marginBottom: '0.5rem'
                                }}>
                                    <strong>{line.speaker === 'ai' ? 'AI: ' : 'Caller: '}</strong>
                                    {line.text}
                                </p>
                            ))}
                        </div>
                    </div>
                    <div className={styles.transcriptActions}>
                        <button className={styles.actionBtnSm}>Copy</button>
                        <button className={styles.actionBtnSm}>Summarize</button>
                        <button className={styles.actionBtnSm}>Create Ticket</button>
                        <button className={styles.actionBtnSm}>Add to CRM</button>
                    </div>
                </section>

                {/* System Health */}
                <section className={styles.healthCard}>
                    <h3>System Health</h3>
                    <div className={styles.healthGrid}>
                        <div className={styles.healthItem}>
                            <div className={`${styles.healthOrb} ${styles.connected}`} />
                            <div>
                                <span>Phone</span>
                                <small>{business?.phone_number || 'Connecting...'}</small>
                            </div>
                        </div>
                        <div className={styles.healthItem}>
                            <div className={`${styles.healthOrb} ${styles.healthy}`} />
                            <div>
                                <span>LLM</span>
                                <small>Active</small>
                            </div>
                        </div>
                        <div className={styles.healthItem}>
                            <div className={`${styles.healthOrb} ${business?.google_calendar_connected ? styles.synced : styles.inactive}`} />
                            <div>
                                <span>Calendar</span>
                                <small>{business?.google_calendar_connected ? 'Synced' : 'Disconnected'}</small>
                            </div>
                        </div>
                        <div className={styles.healthItem}>
                            <div className={`${styles.healthOrb} ${styles.ok}`} />
                            <div>
                                <span>Status</span>
                                <small>Live</small>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Schedule/Booking with REAL TIME */}
                <section className={styles.scheduleCard}>
                    <h3>Schedule / Booking</h3>
                    <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
                        <div style={{ fontSize: '0.9rem', color: '#666' }}>
                            {currentTime.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                        </div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#3d84ff' }}>
                            {currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
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
                                    days.push(<span key={`empty-${i}`} style={{ visibility: 'hidden' }}>0</span>);
                                }
                                for (let i = 1; i <= daysInMonth; i++) {
                                    days.push(
                                        <span key={i} className={i === today ? styles.today : ''}>{i}</span>
                                    );
                                }
                                return days;
                            })()}
                        </div>
                    </div>
                    <button className={styles.blockTimeBtn}>Block time</button>
                </section>

                {/* Knowledge Brain */}
                <section className={styles.knowledgeCard}>
                    <h3>Knowledge Brain</h3>
                    <div className={styles.kbStats}>
                        <div className={styles.kbNumber}>
                            <span className={styles.kbLabel}>KB</span>
                            <span className={styles.kbValue}>{business?.business_info?.length ? Math.round(business.business_info.length / 1024) : 0}</span>
                        </div>
                        <span className={styles.kbUnit}>KB total</span>
                    </div>
                    <div className={styles.kbActions}>
                        <button className={styles.kbBtn}>Train / Update</button>
                    </div>
                </section>
            </aside>

            {/* Toast Notifications */}
            {showToast && (
                <div className={styles.toastContainer}>
                    <div className={styles.toast}>
                        <span className={styles.toastIcon}>✓</span>
                        <span>New booking created</span>
                        <button onClick={() => setShowToast(false)} className={styles.toastClose}>×</button>
                    </div>
                </div>
            )}
        </div>
    );
}
