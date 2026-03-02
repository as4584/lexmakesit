"""
Patch script to inject Voice Settings section into the production settings page.

Run on the server:
    python3 patch_settings_page.py /opt/ai-receptionist/frontend/app/dashboard/settings/page.tsx
"""
import sys
import re

VOICE_SECTION_JSX = r'''
                        {/* Section: Voice Settings */}
                        <section style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', border: '1px solid #eee' }}>
                            <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span>🎙️</span> Voice Settings
                            </h2>
                            <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.9rem' }}>
                                Choose a voice for your AI receptionist or clone your own voice.
                                {voiceSettings?.elevenlabs_voice_name && (
                                    <span style={{ marginLeft: '10px', background: '#eef4ff', padding: '2px 10px', borderRadius: '12px', fontSize: '0.8rem', color: '#3d84ff', fontWeight: 'bold' }}>
                                        Current: {voiceSettings.elevenlabs_voice_name}
                                    </span>
                                )}
                            </p>

                            {/* Voice Cloning */}
                            <VoiceClone
                                hasClone={voiceSettings?.has_clone || false}
                                cloneVoiceId={voiceSettings?.custom_clone_voice_id}
                                cloneVoiceName={voiceSettings?.custom_clone_voice_name}
                                currentVoiceId={voiceSettings?.elevenlabs_voice_id}
                                onCloneChanged={loadVoiceSettings}
                            />

                            {/* Voice Browser */}
                            <div style={{ marginTop: '1.25rem' }}>
                                <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span>🔊</span> Voice Library
                                </h3>
                                <p style={{ color: '#666', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
                                    Browse and preview voices. Click &quot;Use&quot; to set as your receptionist&apos;s voice.
                                </p>
                                <VoiceBrowser
                                    currentVoiceId={voiceSettings?.elevenlabs_voice_id}
                                    onVoiceSelected={handleVoiceSelected}
                                />
                            </div>
                        </section>
'''

VOICE_IMPORTS = """import VoiceBrowser from '@/components/VoiceBrowser';
import VoiceClone from '@/components/VoiceClone';
import { getVoiceSettings, VoiceSettings } from '@/lib/voiceApi';
"""

VOICE_STATE = """
    // Voice settings state
    const [voiceSettings, setVoiceSettings] = useState<VoiceSettings | null>(null);
"""

VOICE_LOADER = """
    // Load voice settings
    async function loadVoiceSettings() {
        try {
            const vs = await getVoiceSettings();
            setVoiceSettings(vs);
        } catch (err) {
            console.log('[VOICE] Could not load voice settings:', err);
        }
    }

    function handleVoiceSelected(voiceId: string, voiceName: string) {
        loadVoiceSettings();
    }
"""

VOICE_EFFECT_CALL = """        loadVoiceSettings();"""


def patch_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Add imports after the existing import block
    # Find the last import line
    import_match = re.search(r"(import [^\n]+\n)(?=\n|'use client'|export|const|function)", content)
    if not import_match:
        # fallback: insert after 'use client' line
        content = content.replace("'use client';", "'use client';\n" + VOICE_IMPORTS, 1)
    else:
        # Insert after the last import
        last_import_end = 0
        for m in re.finditer(r"^import .+$", content, re.MULTILINE):
            last_import_end = m.end()
        if last_import_end > 0:
            content = content[:last_import_end] + "\n" + VOICE_IMPORTS + content[last_import_end:]
        else:
            content = content.replace("'use client';", "'use client';\n" + VOICE_IMPORTS, 1)

    # 2. Add voice state declaration after existing useState lines
    # Find the last useState line in the component
    state_match = list(re.finditer(r'const \[.+?\] = useState.*?\);', content))
    if state_match:
        last_state = state_match[-1]
        insert_pos = last_state.end()
        content = content[:insert_pos] + VOICE_STATE + content[insert_pos:]

    # 3. Add voice loader + handler functions
    # Insert before the first useEffect
    effect_match = re.search(r'\n(\s+)useEffect\(\(\) =>', content)
    if effect_match:
        insert_pos = effect_match.start()
        content = content[:insert_pos] + "\n" + VOICE_LOADER + content[insert_pos:]

    # 4. Add loadVoiceSettings() call inside the existing useEffect that loads business
    # Find the useEffect that calls loadBusiness or getBusiness
    effect_body = re.search(r'useEffect\(\(\) => \{[^}]*?(loadBusiness|getBusiness)[^}]*?\}', content)
    if effect_body:
        # Insert loadVoiceSettings() after the existing function call
        call_match = re.search(r'(loadBusiness|getBusiness)\(\);?', content[effect_body.start():effect_body.end()])
        if call_match:
            abs_pos = effect_body.start() + call_match.end()
            content = content[:abs_pos] + "\n" + VOICE_EFFECT_CALL + content[abs_pos:]

    # 5. Insert the Voice Settings section JSX before Security section
    # Look for the Security & Password section
    security_marker = '{/* Section 3: Security */'
    alt_security_marker = 'Security & Password'
    
    if security_marker in content:
        # Insert before the Security section
        sec_pos = content.index(security_marker)
        # Back up to the <section> tag
        section_start = content.rfind('<section', 0, sec_pos)
        if section_start > 0:
            content = content[:section_start] + VOICE_SECTION_JSX + "\n\n                        " + content[section_start:]
    elif alt_security_marker in content:
        sec_pos = content.index(alt_security_marker)
        section_start = content.rfind('<section', 0, sec_pos)
        if section_start > 0:
            content = content[:section_start] + VOICE_SECTION_JSX + "\n\n                        " + content[section_start:]
    else:
        # Fallback: insert before the FAQ section
        faq_marker = 'Frequently Asked Questions'
        if faq_marker in content:
            faq_pos = content.index(faq_marker)
            section_start = content.rfind('<section', 0, faq_pos)
            if section_start > 0:
                content = content[:section_start] + VOICE_SECTION_JSX + "\n\n                        " + content[section_start:]

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"✅ Patched {filepath}")
    print(f"   - Added voice imports")
    print(f"   - Added voice state")
    print(f"   - Added voice loader functions")
    print(f"   - Added Voice Settings section JSX")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 patch_settings_page.py <path-to-page.tsx>")
        sys.exit(1)
    patch_file(sys.argv[1])
