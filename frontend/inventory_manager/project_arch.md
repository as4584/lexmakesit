🚀 Project Architecture Template (For Copilot)

Use this file as the master template.
Whenever I build a new project, follow this exact structure, folder layout, port rules, deployment pipeline, and Nginx/systemd patterns.

🧱 Core Stack (follow this for all projects)

FastAPI + Uvicorn

Dockerfile for production

docker-compose for building + restarting the service

Nginx reverse proxy → routes requests per project

systemd service → makes Docker stay alive forever

GitHub Actions → deploys automatically on push

DigitalOcean Ubuntu droplet running everything under /srv/<project>

📦 Server Layout (MUST follow this)

All projects live under:

/srv/<project-name>
/srv/portfolio
/srv/inventory_manager
/srv/<future-project>


Every project MUST:

run inside Docker

expose one internal port only

have a matching systemd service

have a matching Nginx block

be deployable by GitHub Actions

use ports in steps of 10:

8000 (portfolio)

8010 (inventory)

8020 (next project)

etc.

🔁 CI/CD Rules (Copilot follow these every time)

Each new project needs a workflow like this:

Run tests, linting, security scans

Build Docker image

SSH into server using secrets:

HOST_IP

SSH_USERNAME

SSH_KEY

cd /srv/<project> and pull latest code

Run

docker compose up -d --build


Restart systemd service

Reload Nginx (only if reverse proxy changed)

Copilot → create this workflow automatically for future repos.

📁 Required Files (Copilot must generate for ANY project)
Dockerfile
docker-compose.yml
.github/workflows/deploy.yml
project_name.service (systemd file)
nginx-project-name.conf (if needed)

🧩 Dockerfile Pattern

Copilot: always generate a Dockerfile like this:

Start from Python 3.x

Install deps from requirements.txt

Expose one internal port

Run uvicorn with host 0.0.0.0 app.main:app or main:app

Use --workers 2 --proxy-headers

🔧 docker-compose.yml Pattern

Copilot should always include:

services:
  app:
    build: .
    restart: always
    ports:
      - "PORT:PORT"


Replace PORT with whatever port the project is assigned.

🛠 systemd Service Template

Copilot → ALWAYS generate this:

[Unit]
Description=<PROJECT> Service
After=network.target docker.service
Requires=docker.service

[Service]
User=lex
WorkingDirectory=/srv/<PROJECT>
ExecStart=/usr/bin/docker compose -f /srv/<PROJECT>/docker-compose.yml up -d --build
ExecStop=/usr/bin/docker compose -f /srv/<PROJECT>/docker-compose.yml down
Restart=always

[Install]
WantedBy=multi-user.target

🌐 Nginx Template

Copilot must always follow this routing pattern:

location /<PROJECT>/ {
    proxy_pass http://127.0.0.1:PORT/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

🔒 Required Repo Secrets

Every project needs these in GitHub:

HOST_IP

SSH_USERNAME

SSH_KEY

No exceptions.

📐 Port Rules (Copilot follow this automatically)

Use these ranges:

8000 → portfolio

8010 → inventory

8020 → next

8030 → next

continue stepping by 10

🧪 Testing Pipeline

Copilot should always generate:

syntax check

dependency vuln scan

pytest

ruff or flake8 lint

docker build validation

🎯 Mission

This file tells Copilot:

how all your projects are structured

how to set up deployment for new ones

what ports to use

what systemd + Nginx must look like

how your server expects every project to behave

This guarantees everything you build works the same way across all lexmakesit projects.