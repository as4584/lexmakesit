from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import click
import jwt
import requests


ENV_FILE = os.path.expanduser("~/.adminctl.env")


def _read_env_file(path: str) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not os.path.exists(path):
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _make_token(admin_user: str, tenant: Optional[str], private_key: str, ttl_seconds: int = 60) -> str:
    now = int(time.time())
    payload = {
        "iss": "adminctl",
        "sub": admin_user,
        "scope": "admin",
        "iat": now,
        "exp": now + ttl_seconds,
    }
    if tenant:
        payload["tenant_id"] = tenant
    return jwt.encode(payload, private_key, algorithm="HS256")


@dataclass
class Client:
    base_url: str
    admin_user: str
    private_key: str

    def _headers(self, tenant: Optional[str]) -> Dict[str, str]:
        token = _make_token(self.admin_user, tenant, self.private_key)
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def request(self, method: str, path: str, *, tenant: Optional[str] = None, json_body: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = self.base_url.rstrip("/") + path
        headers = self._headers(tenant)
        return requests.request(method, url, headers=headers, json=json_body, timeout=10)


def _get_client(admin_user: str) -> Client:
    env = _read_env_file(ENV_FILE)
    private_key = env.get("ADMIN_PRIVATE_KEY") or os.environ.get("ADMIN_PRIVATE_KEY")
    if not private_key:
        click.echo("Missing ADMIN_PRIVATE_KEY in ~/.adminctl.env or environment", err=True)
        sys.exit(2)
    base_url = os.environ.get("ADMIN_API_URL", "http://localhost:8080")
    return Client(base_url=base_url, admin_user=admin_user, private_key=private_key)


@click.group()
def adminctl():
    """Admin CLI for tenant plans and flags."""


@adminctl.command("set-plan")
@click.option("--tenant", required=True, help="Tenant ID")
@click.option("--plan", required=True, type=click.Choice(["starter", "core", "pro", "enterprise"], case_sensitive=False))
@click.option("--admin-user", required=True, help="Admin user name")
def set_plan(tenant: str, plan: str, admin_user: str):
    client = _get_client(admin_user)
    resp = client.request("PUT", f"/admin/tenants/{tenant}/plan", tenant=tenant, json_body={"plan": plan.lower()})
    click.echo(resp.text if resp.text else "")
    if not resp.ok:
        sys.exit(1)


@adminctl.command("set-flag")
@click.option("--tenant", required=True, help="Tenant ID")
@click.option("--flag", required=True, help="Flag name")
@click.option("--enable", required=True, type=bool, help="Enable (true/false)")
@click.option("--admin-user", required=True, help="Admin user name")
def set_flag(tenant: str, flag: str, enable: bool, admin_user: str):
    client = _get_client(admin_user)
    resp = client.request("PUT", f"/admin/tenants/{tenant}/flags/{flag}", tenant=tenant, json_body={"enable": bool(enable)})
    click.echo(resp.text if resp.text else "")
    if not resp.ok:
        sys.exit(1)


@adminctl.command("show-flags")
@click.option("--tenant", required=True, help="Tenant ID")
@click.option("--admin-user", required=False, default="system", help="Admin user name")
def show_flags(tenant: str, admin_user: str):
    client = _get_client(admin_user)
    resp = client.request("GET", f"/admin/tenants/{tenant}/flags", tenant=tenant)
    if resp.ok:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        click.echo(json.dumps(data, indent=2, sort_keys=True))
    else:
        click.echo(resp.text if resp.text else "")
        sys.exit(1)


# ---------------------------------------------------------------------------
# User / number management helpers
# ---------------------------------------------------------------------------


@adminctl.command("create-user")
@click.option("--username", required=True, help="Login username")
@click.option("--password", required=True, help="Plain-text password (will be hashed server-side)")
@click.option("--full-name", default=None, help="Display name")
@click.option("--tenant-name", default=None, help="Business/tenant display name (default: capitalised username)")
@click.option("--plan", type=click.Choice(["starter", "core", "pro", "enterprise"], case_sensitive=False), default=None, help="Set plan after creation")
@click.option("--admin-user", required=False, default="system", help="Admin identity for audit")
def create_user(username: str, password: str, full_name: Optional[str], tenant_name: Optional[str], plan: Optional[str], admin_user: str):
    """Create a user + tenant via the auth API, then optionally set a plan."""
    client = _get_client(admin_user)

    # 1. Signup
    signup_body: Dict[str, Any] = {"username": username, "password": password}
    if full_name:
        signup_body["full_name"] = full_name
    if tenant_name:
        signup_body["tenant_name"] = tenant_name

    resp = client.request("POST", "/api/auth/signup", json_body=signup_body)
    if not resp.ok:
        click.echo(f"signup failed: {resp.text}", err=True)
        sys.exit(1)

    data = resp.json()
    click.echo(f"Created user '{data['user']['username']}' (id={data['user']['id']}, tenant={data['user']['tenant_id']})")

    # 2. Set plan (optional)
    if plan:
        tenant_id = data["user"]["tenant_id"]
        resp2 = client.request("PUT", f"/admin/tenants/{tenant_id}/plan", tenant=tenant_id, json_body={"plan": plan.lower()})
        if resp2.ok:
            click.echo(f"Plan set to '{plan}' for tenant '{tenant_id}'")
        else:
            click.echo(f"set-plan failed: {resp2.text}", err=True)
            sys.exit(1)


@adminctl.command("provision-number")
@click.option("--tenant", required=True, help="Tenant ID to assign the number to")
@click.option("--area-code", default=None, help="Preferred US area code (optional)")
@click.option("--admin-user", required=False, default="system", help="Admin identity for audit")
def provision_number(tenant: str, area_code: Optional[str], admin_user: str):
    """Buy a US local Twilio number and assign it to a tenant."""
    client = _get_client(admin_user)
    body: Dict[str, Any] = {}
    if area_code:
        body["area_code"] = area_code

    resp = client.request("POST", f"/admin/tenants/{tenant}/phone-number", tenant=tenant, json_body=body)
    if resp.ok:
        data = resp.json()
        click.echo(f"Provisioned {data['phone_number']} (SID={data['twilio_sid']}) → tenant '{tenant}'")
    else:
        click.echo(f"provision failed: {resp.text}", err=True)
        sys.exit(1)


@adminctl.command("show-user")
@click.option("--username", required=True, help="Username to look up")
@click.option("--admin-user", required=False, default="system", help="Admin identity")
def show_user(username: str, admin_user: str):
    """Look up a user by username (requires the user's auth token – uses login)."""
    click.echo(f"Use POST /api/auth/login with username='{username}' to obtain a token, then GET /api/auth/me.")


if __name__ == "__main__":
    adminctl()
