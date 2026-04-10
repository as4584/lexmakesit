path = '/opt/ai-receptionist/docker-compose.prod.yml'
with open(path) as f:
    content = f.read()

# Fix: the sed went wrong. Let me check and fix the line.
# Find and fix the broken line
broken = '    ports:\n      - " 8002:8002\n command: uvicorn ai_receptionist.app.main:app --host 0.0.0.0 --port 8002 --workers 4'
if broken in content:
    fixed = '    ports:\n      - "8002:8002"\n    command: uvicorn ai_receptionist.app.main:app --host 0.0.0.0 --port 8002 --workers 4'
    content = content.replace(broken, fixed, 1)
    print('Fixed broken sed result')
else:
    # Maybe it's already correct or needs different fix
    print('Broken pattern not found. Current relevant section:')
    for i, line in enumerate(content.split('\n')):
        if '8002' in line or 'ports' in line or 'command' in line:
            print(f'  line {i}: {repr(line)}')

with open(path, 'w') as f:
    f.write(content)
print('Done')
