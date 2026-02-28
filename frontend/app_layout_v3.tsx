'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { logout, getBusiness, type Business } from '../../lib/api';
import styles from './dashboard.module.css';

export default function AppLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [business, setBusiness] = useState<Business | null>(null);

    useEffect(() => {
        getBusiness()
            .then(data => setBusiness(data))
            .catch(() => console.log('Not logged in or no business'));
    }, []);

    const handleLogout = async () => {
        await logout();
        router.push('/login');
    };

    return (
        <div className={styles.appContainer}>
            <header className={styles.header}>
                <div className={styles.headerContent}>
                    <div className={styles.logo} onClick={() => router.push('/app')}>
                        <span style={{ color: '#3d84ff', fontWeight: 'bold', fontSize: '1.2rem' }}>AI Receptionist</span>
                    </div>

                    <nav className={styles.nav}>
                        <button onClick={() => router.push('/app')} className={styles.navLink}>Dashboard</button>
                        <button onClick={() => window.open('https://lexmakesit.com/#pricing', '_blank')} className={styles.navLink}>
                            Pricing & Plans
                        </button>
                        <button onClick={() => router.push('/app/settings')} className={styles.navLink}>Settings</button>
                    </nav>

                    <div className={styles.headerRight}>
                        {business?.phone_number && (
                            <div className={styles.phoneBadge}>
                                📞 {business.phone_number}
                            </div>
                        )}
                        <button onClick={handleLogout} className={styles.logoutBtn}>Logout</button>
                    </div>
                </div>
            </header>

            <main className={styles.main}>
                {children}
            </main>
        </div>
    );
}
