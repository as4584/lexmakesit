8576W23415EW3452W'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createBusiness, getAvailableNumbers, redirectToGoogleOAuth } from '../../../lib/api';
import styles from '../../login/login.module.css';

type Step = 1 | 2 | 3 | 4;

export default function OnboardingPage() {
    const router = useRouter();

    // Step management
    const [currentStep, setCurrentStep] = useState<Step>(1);

    // Step 1: Business Profile
    const [businessName, setBusinessName] = useState('');
    const [industry, setIndustry] = useState('');
    const [businessDescription, setBusinessDescription] = useState('');

    // Step 2: Phone Number
    const [availableNumbers, setAvailableNumbers] = useState<{ phoneNumber: string, friendlyName: string }[]>([]);
    const [selectedNumber, setSelectedNumber] = useState('');
    const [loadingNumbers, setLoadingNumbers] = useState(false);

    // Step 3: AI Persona
    const [greetingStyle, setGreetingStyle] = useState('professional');
    const [businessHours, setBusinessHours] = useState('9 AM - 5 PM, Monday - Friday');
    const [commonServices, setCommonServices] = useState('');
    const [faqEntries, setFaqEntries] = useState<{ question: string, answer: string }[]>([
        { question: '', answer: '' }
    ]);

    // Step 4: Finalize
    const [timezone, setTimezone] = useState('America/New_York');
    const [calConnected, setCalConnected] = useState(false);

    // General state
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    // Load Twilio numbers when reaching step 2
    useEffect(() => {
        if (currentStep === 2 && availableNumbers.length === 0) {
            setLoadingNumbers(true);
            getAvailableNumbers()
                .then(numbers => {
                    setAvailableNumbers(numbers);
                    if (numbers.length > 0) {
                        setSelectedNumber(numbers[0].phoneNumber);
                    }
                })
                .catch(err => {
                    console.error('Failed to load numbers:', err);
                    setError('Could not load available phone numbers. Please try again.');
                })
                .finally(() => setLoadingNumbers(false));
        }
    }, [currentStep, availableNumbers.length]);

    const handleAddFaq = () => {
        setFaqEntries([...faqEntries, { question: '', answer: '' }]);
    };

    const handleRemoveFaq = (index: number) => {
        setFaqEntries(faqEntries.filter((_, i) => i !== index));
    };

    const handleFaqChange = (index: number, field: 'question' | 'answer', value: string) => {
        const updated = [...faqEntries];
        updated[index][field] = value;
        setFaqEntries(updated);
    };

    const handleConnectCalendar = () => {
        try {
            // If we have a business name, we should probably save partial state or just pass it
            // For now, use the standard OAuth redirect
            redirectToGoogleOAuth('demo-biz-123'); // Using placeholder ID for now
        } catch (err) {
            setError('Failed to start calendar connection');
        }
    };

    const handleNext = () => {
        if (currentStep < 4) {
            setCurrentStep((currentStep + 1) as Step);
        }
    };

    const handleBack = () => {
        if (currentStep > 1) {
            setCurrentStep((currentStep - 1) as Step);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await createBusiness({
                name: businessName,
                phone_number: selectedNumber || undefined,
                timezone,
            });

            // Success! Head to the dashboard
            router.push('/app');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create business profile');
        } finally {
            setLoading(false);
        }
    };

    const stepTitles = ['Business', 'Number', 'AI Style', 'Finalize'];

    return (
        <div className={styles.container}>
            <div className={styles.card} style={{ maxWidth: '600px', width: '95%' }}>
                {/* Progress Indicator */}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
                    {[1, 2, 3, 4].map((step) => (
                        <div key={step} style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            flex: 1
                        }}>
                            <div style={{
                                width: '40px',
                                height: '40px',
                                borderRadius: '50%',
                                background: currentStep >= step ? 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)' : '#e0e0e0',
                                color: currentStep >= step ? 'white' : '#666',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontWeight: 'bold',
                                transition: 'all 0.3s ease'
                            }}>
                                {currentStep > step ? '✓' : step}
                            </div>
                            <span style={{
                                fontSize: '0.75rem',
                                marginTop: '0.5rem',
                                color: currentStep >= step ? '#3d84ff' : '#999'
                            }}>
                                {stepTitles[step - 1]}
                            </span>
                        </div>
                    ))}
                </div>

                <form onSubmit={handleSubmit} className={styles.form}>
                    {error && <div className={styles.error} style={{
                        background: '#fff5f5',
                        color: '#c53030',
                        padding: '1rem',
                        borderRadius: '0.5rem',
                        marginBottom: '1rem',
                        border: '1px solid #feb2b2'
                    }}>{error}</div>}

                    {/* Step 1: Business Profile */}
                    {currentStep === 1 && (
                        <div>
                            <h2 style={{ marginBottom: '1rem' }}>Business Profile</h2>
                            <div className={styles.field}>
                                <label>Business Name *</label>
                                <input
                                    type="text"
                                    value={businessName}
                                    onChange={(e) => setBusinessName(e.target.value)}
                                    required
                                    placeholder="e.g., Acme Dental"
                                />
                            </div>
                            <div className={styles.field}>
                                <label>Industry</label>
                                <input
                                    type="text"
                                    value={industry}
                                    onChange={(e) => setIndustry(e.target.value)}
                                    placeholder="e.g., Healthcare"
                                />
                            </div>
                        </div>
                    )}

                    {/* Step 2: Phone Number */}
                    {currentStep === 2 && (
                        <div>
                            <h2 style={{ marginBottom: '1rem' }}>Choose Phone Number</h2>
                            {loadingNumbers ? <p>Loading numbers...</p> : (
                                <div className={styles.field}>
                                    <select
                                        value={selectedNumber}
                                        onChange={(e) => setSelectedNumber(e.target.value)}
                                        style={{ width: '100%', padding: '0.8rem', borderRadius: '10px' }}
                                    >
                                        <option value="">Select a number...</option>
                                        {availableNumbers.map(n => (
                                            <option key={n.phoneNumber} value={n.phoneNumber}>{n.friendlyName}</option>
                                        ))}
                                    </select>
                                    {availableNumbers.length === 0 && (
                                        <p style={{ color: '#718096', fontSize: '0.9rem', marginTop: '1rem' }}>
                                            No personal numbers found. We've set up a <strong>Pilot Demo Line</strong> for your account.
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 3: AI Persona */}
                    {currentStep === 3 && (
                        <div>
                            <h2 style={{ marginBottom: '1.5rem' }}>AI Persona</h2>
                            <div className={styles.field}>
                                <label>Greeting Style</label>
                                <select value={greetingStyle} onChange={(e) => setGreetingStyle(e.target.value)}>
                                    <option value="professional">Professional</option>
                                    <option value="friendly">Friendly</option>
                                </select>
                            </div>
                            <div className={styles.field}>
                                <label>FAQs (AI Knowledge)</label>
                                {faqEntries.map((faq, idx) => (
                                    <div key={idx} style={{ marginBottom: '1rem' }}>
                                        <input
                                            placeholder="Question"
                                            value={faq.question}
                                            onChange={(e) => handleFaqChange(idx, 'question', e.target.value)}
                                            style={{ marginBottom: '0.5rem' }}
                                        />
                                        <textarea
                                            placeholder="Answer"
                                            value={faq.answer}
                                            onChange={(e) => handleFaqChange(idx, 'answer', e.target.value)}
                                        />
                                    </div>
                                ))}
                                <button type="button" onClick={handleAddFaq}>+ Add FAQ</button>
                            </div>
                        </div>
                    )}

                    {/* Step 4: Finalize & Calendar */}
                    {currentStep === 4 && (
                        <div>
                            <h2 style={{ marginBottom: '1rem' }}>Finalize Setup</h2>
                            <div className={styles.field}>
                                <label>Timezone</label>
                                <select value={timezone} onChange={(e) => setTimezone(e.target.value)}>
                                    <option value="America/New_York">Eastern Time</option>
                                    <option value="America/Los_Angeles">Pacific Time</option>
                                </select>
                            </div>

                            <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#f0f9ff', borderRadius: '16px', border: '1px solid #bee3f8' }}>
                                <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: '#2b6cb0' }}>🚀 Calendar Access</h3>
                                <p style={{ fontSize: '0.9rem', color: '#4a5568', marginBottom: '1rem' }}>
                                    Connect your Google Calendar so the AI can book appointments for you.
                                </p>
                                <button
                                    type="button"
                                    onClick={handleConnectCalendar}
                                    style={{
                                        width: '100%',
                                        padding: '0.8rem',
                                        background: 'white',
                                        border: '2px solid #3d84ff',
                                        borderRadius: '12px',
                                        color: '#3d84ff',
                                        fontWeight: 'bold',
                                        cursor: 'pointer'
                                    }}
                                >
                                    🔗 Connect Google Calendar
                                </button>
                            </div>

                            <div style={{ margin: '1.5rem 0', fontSize: '0.9rem', color: '#718096' }}>
                                <p>By launching, your AI receptionist will be active on <strong>{selectedNumber || 'your demo line'}</strong>.</p>
                            </div>
                        </div>
                    )}

                    {/* Nav Buttons */}
                    <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                        {currentStep > 1 && (
                            <button type="button" onClick={handleBack} style={{ flex: 1 }}>Back</button>
                        )}
                        <button
                            type={currentStep === 4 ? "submit" : "button"}
                            onClick={currentStep < 4 ? handleNext : undefined}
                            style={{
                                flex: 2,
                                background: 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)',
                                color: 'white',
                                border: 'none',
                                padding: '0.8rem',
                                borderRadius: '12px',
                                fontWeight: 'bold'
                            }}
                            disabled={loading}
                        >
                            {loading ? 'Launching...' : currentStep === 4 ? 'Launch AI Receptionist' : 'Continue'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
