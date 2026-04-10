path = '/opt/ai-receptionist/docker-compose.prod.yml'
with open(path) as f:
    content = f.read()

# The broken line has a literal \n in it (not an actual newline)
# Let's find and fix line 24
lines = content.split('\n')
for i, line in enumerate(lines):
    if '8002:8002' in line and 'command' in line:
        # This is the broken combined line - split it
        lines[i] = '      - "8002:8002"'
        lines.insert(i+1, '    command: uvicorn ai_receptionist.app.main:app --host 0.0.0.0 --port 8002 --workers 4')
        print(f'Fixed line {i}: {repr(line)}')
        break
    elif '8002:8002' in line and line.strip().startswith('-'):
        # Check if the value is malformed
        if line.strip() != '- "8002:8002"':
            lines[i] = '      - "8002:8002"'
            print(f'Fixed port line {i}: {repr(line)} -> "      - \\"8002:8002\\""')
            break

content = '\n'.join(lines)

with open(path, 'w') as f:
    f.write(content)

# Print relevant lines for verification
with open(path) as f:
    new_lines = f.readlines()
    for i, line in enumerate(new_lines):
        if '8002' in line or ('ports' in line and i < 30) or ('command' in line and i < 30):
            print(f'  line {i+1}: {repr(line.rstrip())}')
