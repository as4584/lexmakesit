import sys

path = '/opt/ai-receptionist/frontend/lib/hooks.ts'
with open(path) as f:
    content = f.read()

# Add React import
old_import = "import useSWR from 'swr';"
new_import = "import useSWR from 'swr';\nimport { useEffect, useRef } from 'react';"
content = content.replace(old_import, new_import, 1)

hook = """
export function useCallStream(onNewCall: (call: any) => void) {
    const onNewCallRef = useRef(onNewCall);
    useEffect(() => { onNewCallRef.current = onNewCall; }, [onNewCall]);

    useEffect(() => {
        let es: EventSource | null = null;
        let retryTimeout: ReturnType<typeof setTimeout> | null = null;

        function connect() {
            es = new EventSource('/api/business/events/calls', { withCredentials: true });
            es.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'new_call') {
                        onNewCallRef.current(data);
                    }
                } catch {}
            };
            es.onerror = () => {
                es?.close();
                retryTimeout = setTimeout(connect, 5000);
            };
        }

        connect();
        return () => {
            es?.close();
            if (retryTimeout) clearTimeout(retryTimeout);
        };
    }, []);
}
"""

if 'useCallStream' not in content:
    content += hook

with open(path, 'w') as f:
    f.write(content)

print('hooks.ts updated')
