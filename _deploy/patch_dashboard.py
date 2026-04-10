import sys

path = '/opt/ai-receptionist/frontend/app/dashboard/DashboardContent.tsx'
with open(path) as f:
    content = f.read()

# Replace hooks import to add useCallStream
old_import = "import { useUser, useBusiness, useRecentCalls } from '@/lib/hooks';"
new_import = "import { useUser, useBusiness, useRecentCalls, useCallStream } from '@/lib/hooks';"
content = content.replace(old_import, new_import, 1)

# Find the line with mutateCalls and insert useCallStream call after the hook declarations
# We look for the line that has mutateCalls declaration and insert after it
old_hooks = "    const { calls: recentCalls, isLoading: callsLoading, isError: callsError, mutate: mutateCalls } = useRecentCalls();"
new_hooks = (
    "    const { calls: recentCalls, isLoading: callsLoading, isError: callsError, mutate: mutateCalls } = useRecentCalls();\n"
    "    useCallStream(() => { mutateCalls(); });"
)
content = content.replace(old_hooks, new_hooks, 1)

with open(path, 'w') as f:
    f.write(content)

print('DashboardContent.tsx updated')
