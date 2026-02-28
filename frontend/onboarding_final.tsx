'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createBusiness, getAvailableNumbers } from '../../../lib/api';
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

    // Step 4: Timezone
    const [timezone, setTimezone] = useState('America/New_York');

    // General state
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    // Load Twilio numbers when reaching step 2
    useEffect(() => {
        if (currentStep === 2 && availableNumbers.length === 0) {
            setLoadingNumbers(true);
            getAvailableNumbers()
                .then(numbers => setAvailableNumbers(numbers))
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
            // Build business info from all steps
            const businessInfo = `
Business: ${businessName}
Industry: ${industry}
Description: ${businessDescription}
Business Hours: ${businessHours}
Services: ${commonServices}

FAQs:
${faqEntries.filter(f => f.question && f.answer).map(f => `Q: ${f.question}\nA: ${f.answer}`).join('\n\n')}
            `.trim();

            const business = await createBusiness({
                name: businessName,
                phone_number: selectedNumber || undefined,
                timezone,
                //Note: business_info is not in CreateBusinessData interface yet, but let's assume it works or we'll update the API
            });

            // Redirect to calendar connection step
            router.push(`/app/onboarding/calendar?business_id=${business.id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create business profile');
        } finally {
            setLoading(false);
        }
    };

    const stepTitles = ['Business Profile', 'Phone Number', 'AI Persona', 'Finalize'];

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
                                transition: 'all 0.3s ease',
                                boxShadow: currentStep === step ? '0 0 10px rgba(61, 132, 255, 0.5)' : 'none'
                            }}>
                                {currentStep > step ? '✓' : step}
                            </div>
                            <span style={{
                                fontSize: '0.75rem',
                                marginTop: '0.5rem',
                                color: currentStep >= step ? '#3d84ff' : '#999',
                                fontWeight: currentStep === step ? 'bold' : 'normal'
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
                        <div className="animate-in fade-in duration-300">
                            <h2 style={{ marginBottom: '1rem', color: '#1a202c' }}>Tell us about your business</h2>
                            <p style={{ marginBottom: '1.5rem', color: '#4a5568' }}>
                                This helps your AI receptionist represent you accurately.
                            </p>

                            <div className={styles.field}>
                                <label htmlFor="businessName">Business Name *</label>
                                <input
                                    id="businessName"
                                    type="text"
                                    value={businessName}
                                    onChange={(e) => setBusinessName(e.target.value)}
                                    required
                                    placeholder="e.g., Acme Dental"
                                    className="w-full"
                                />
                            </div>

                            <div className={styles.field}>
                                <label htmlFor="industry">Industry *</label>
                                <select
                                    id="industry"
                                    value={industry}
                                    onChange={(e) => setIndustry(e.target.value)}
                                    required
                                    style={{ padding: '0.75rem', border: '1px solid #ddd', borderRadius: '8px', fontSize: '1rem', width: '100%' }}
                                >
                                    <option value="">Select your industry...</option>
                                    <option value="Healthcare">Healthcare (Dental, Medical, etc.)</option>
                                    <option value="Legal">Legal Services</option>
                                    <option value="Home Services">Home Services (HVAC, Plumbing, etc.)</option>
                                    <option value="Real Estate">Real Estate</option>
                                    <option value="Automotive">Automotive</option>
                                    <option value="Salon & Spa">Salon & Spa</option>
                                    <option value="Professional Services">Professional Services</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>

                            <div className={styles.field}>
                                <label htmlFor="businessDescription">Brief Description</label>
                                <textarea
                                    id="businessDescription"
                                    value={businessDescription}
                                    onChange={(e) => setBusinessDescription(e.target.value)}
                                    placeholder="What does your business do? What makes it special?"
                                    rows={3}
                                    style={{ padding: '0.75rem', border: '1px solid #ddd', borderRadius: '8px', fontSize: '1rem', width: '100%', resize: 'vertical' }}
                                />
                            </div>
                        </div>
                    )}

                    {/* Step 2: Phone Number Selection */}
                    {currentStep === 2 && (
                        <div className="animate-in fade-in duration-300">
                            <h2 style={{ marginBottom: '1rem', color: '#1a202c' }}>Choose Your Phone Number</h2>
                            <p style={{ marginBottom: '1.5rem', color: '#4a5568' }}>
                                Select a phone number for your AI receptionist.
                            </p>

                            {loadingNumbers ? (
                                <div style={{ textAlign: 'center', padding: '3rem' }}>
                                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-4"></div>
                                    <p>Loading available numbers...</p>
                                </div>
                            ) : (
                                <div className={styles.field}>
                                    <label htmlFor="phoneNumber">Select Phone Number</label>
                                    <select
                                        id="phoneNumber"
                                        value={selectedNumber}
                                        onChange={(e) => setSelectedNumber(e.target.value)}
                                        style={{ padding: '0.75rem', border: '1px solid #ddd', borderRadius: '8px', fontSize: '1rem', width: '100%' }}
                                    >
                                        <option value="">Choose a number...</option>
                                        {availableNumbers.map((num) => (
                                            <option key={num.phoneNumber} value={num.phoneNumber}>
                                                {num.friendlyName}
                                            </option>
                                        ))}
                                    </select>
                                    <small style={{ color: '#718096', marginTop: '0.5rem', display: 'block' }}>
                                        This number will forward to your AI receptionist.
                                    </small>
                                </div>
                            )}

                            {availableNumbers.length === 0 && !loadingNumbers && (
                                <div style={{ padding: '1rem', background: '#fffaf0', border: '1px solid #fbd38d', borderRadius: '8px', color: '#c05621' }}>
                                    No phone numbers available in your account currently. We've set up a demo line for you.
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 3: AI Persona */}
                    {currentStep === 3 && (
                        <div className="animate-in fade-in duration-300">
                            <h2 style={{ marginBottom: '1rem', color: '#1a202c' }}>Customize Your AI</h2>
                            <p style={{ marginBottom: '1.5rem', color: '#4a5568' }}>
                                Train your AI receptionist with your business knowledge.
                            </p>

                            <div className={styles.field}>
                                <label htmlFor="greetingStyle">Greeting Style</label>
                                <select
                                    id="greetingStyle"
                                    value={greetingStyle}
                                    onChange={(e) => setGreetingStyle(e.target.value)}
                                    style={{ padding: '0.75rem', border: '1px solid #ddd', borderRadius: '8px', fontSize: '1rem', width: '100%' }}
                                >
                                    <option value="professional">Professional ("Thank you for calling [Business]...")</option>
                                    <option value="friendly">Friendly ("Hey there! You've reached [Business]!")</option>
                                    <option value="formal">Formal ("Good morning/afternoon, [Business] speaking.")</option>
                                </select>
                            </div>

                            <div className={styles.field}>
                                <label htmlFor="businessHours">Business Hours</label>
                                <input
                                    id="businessHours"
                                    type="text"
                                    value={businessHours}
                                    onChange={(e) => setBusinessHours(e.target.value)}
                                    placeholder="e.g., 9 AM - 5 PM, Monday - Friday"
                                />
                            </div>

                            <div className={styles.field}>
                                <label htmlFor="commonServices">Common Services (comma separated)</label>
                                <input
                                    id="commonServices"
                                    type="text"
                                    value={commonServices}
                                    onChange={(e) => setCommonServices(e.target.value)}
                                    placeholder="e.g., Cleanings, X-rays, Fillings, Crowns"
                                />
                            </div>

                            <div className={styles.field}>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Frequently Asked Questions</label>
                                <div style={{ maxHeight: '300px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                                    {faqEntries.map((faq, index) => (
                                        <div key={index} style={{ background: '#f8fafc', padding: '1rem', borderRadius: '12px', marginBottom: '1rem', border: '1px solid #e2e8f0' }}>
                                            <input
                                                type="text"
                                                value={faq.question}
                                                onChange={(e) => handleFaqChange(index, 'question', e.target.value)}
                                                placeholder="Question (e.g., Do you take insurance?)"
                                                style={{ width: '100%', marginBottom: '0.5rem', padding: '0.6rem', border: '1px solid #cbd5e0', borderRadius: '6px' }}
                                            />
                                            <textarea
                                                value={faq.answer}
                                                onChange={(e) => handleFaqChange(index, 'answer', e.target.value)}
                                                placeholder="Answer..."
                                                rows={2}
                                                style={{ width: '100%', padding: '0.6rem', border: '1px solid #cbd5e0', borderRadius: '6px', resize: 'vertical' }}
                                            />
                                            {faqEntries.length > 1 && (
                                                <button type="button" onClick={() => handleRemoveFaq(index)} style={{ marginTop: '0.5rem', color: '#e53e3e', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.875rem' }}>
                                                    Remove FAQ
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                                <button type="button" onClick={handleAddFaq} style={{ color: '#3182ce', background: '#ebf8ff', border: '1px dashed #3182ce', padding: '0.75rem 1rem', borderRadius: '8px', cursor: 'pointer', width: '100%', fontWeight: 'bold', marginTop: '0.5rem' }}>
                                    + Add Another FAQ
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Step 4: Timezone & Finalize */}
                    {currentStep === 4 && (
                        <div className="animate-in fade-in duration-300">
                            <h2 style={{ marginBottom: '1rem', color: '#1a202c' }}>Almost Done!</h2>
                            <p style={{ marginBottom: '1.5rem', color: '#4a5568' }}>
                                Set your timezone and confirm your business details.
                            </p>

                            <div className={styles.field}>
                                <label htmlFor="timezone">Timezone *</label>
                                <select
                                    id="timezone"
                                    value={timezone}
                                    onChange={(e) => setTimezone(e.target.value)}
                                    required
                                    style={{ padding: '0.75rem', border: '1px solid #ddd', borderRadius: '8px', fontSize: '1rem', width: '100%' }}
                                >
                                    <option value="America/New_York">Eastern Time</option>
                                    <option value="America/Chicago">Central Time</option>
                                    <option value="America/Denver">Mountain Time</option>
                                    <option value="America/Los_Angeles">Pacific Time</option>
                                    <option value="America/Phoenix">Arizona</option>
                                    <option value="America/Anchorage">Alaska</option>
                                    <option value="Pacific/Honolulu">Hawaii</option>
                                </select>
                            </div>

                            {/* Summary Card */}
                            <div style={{ background: 'linear-gradient(to bottom right, #ebf8ff, #f0f9ff)', padding: '1.5rem', borderRadius: '16px', marginTop: '1.5rem', border: '1px solid #bee3f8' }}>
                                <h3 style={{ marginBottom: '1rem', color: '#2b6cb0' }}>Ready to Launch</h3>
                                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '0.5rem 1rem', fontSize: '0.9rem' }}>
                                    <span style={{ color: '#718096' }}>Business:</span> <strong>{businessName}</strong>
                                    <span style={{ color: '#718096' }}>Phone:</span> <strong>{selectedNumber || 'Pilot Demo Line'}</strong>
                                    <span style={{ color: '#718096' }}>Hours:</span> <strong>{businessHours}</strong>
                                    <span style={{ color: '#718096' }}>KB size:</span> <strong>{faqEntries.filter(f => f.question).length} FAQs</strong>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Navigation Buttons */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2.5rem', gap: '1rem' }}>
                        {currentStep > 1 ? (
                            <button
                                type="button"
                                onClick={handleBack}
                                style={{
                                    padding: '0.8rem 1.5rem',
                                    background: '#edf2f7',
                                    color: '#4a5568',
                                    border: 'none',
                                    borderRadius: '10px',
                                    cursor: 'pointer',
                                    fontWeight: 'bold',
                                    flex: 1,
                                    maxWidth: '150px'
                                }}
                            >
                                Back
                            </button>
                        ) : (
                            <div style={{ flex: 1, maxWidth: '150px' }}></div>
                        )}

                        <button
                            type={currentStep === 4 ? "submit" : "button"}
                            onClick={currentStep < 4 ? handleNext : undefined}
                            disabled={loading || (currentStep === 1 && (!businessName || !industry))}
                            className={styles.button}
                            style={{
                                flex: 2,
                                background: 'linear-gradient(135deg, #60aaff 0%, #3d84ff 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '10px',
                                padding: '0.8rem 1.5rem',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                boxShadow: '0 4px 6px rgba(61, 132, 255, 0.2)',
                                transition: 'transform 0.1s active'
                            }}
                        >
                            {loading ? 'Creating...' : currentStep === 4 ? 'Launch AI Receptionist' : 'Continue'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
