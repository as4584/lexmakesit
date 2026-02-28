"""
Authentication service for Lightspeed X-Series API.
Handles token management and OAuth flow if needed.
"""
import os
from datetime import datetime, timedelta
from typing import Any

import requests


class LightspeedAuth:
    """Service for Lightspeed authentication and token management."""

    def __init__(self):
        """Initialize auth service."""
        self.api_token = os.getenv('LS_X_API_TOKEN')
        self.client_id = os.getenv('LS_CLIENT_ID')
        self.client_secret = os.getenv('LS_CLIENT_SECRET')
        self.redirect_uri = os.getenv('LS_REDIRECT_URI')
        self.refresh_token = os.getenv('LS_REFRESH_TOKEN')

        # Token expiry tracking
        self.token_expires_at = None
        self.token_type = 'Bearer'

    def is_token_valid(self) -> bool:
        """Check if current token is valid and not expired."""
        if not self.api_token:
            return False

        return not (self.token_expires_at and datetime.now() >= self.token_expires_at)

    def get_auth_url(self, state: str | None = None) -> str:
        """Generate OAuth authorization URL."""
        if not self.client_id or not self.redirect_uri:
            raise ValueError("OAuth not configured - missing client_id or redirect_uri")

        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'read write'  # Adjust scopes as needed
        }

        if state:
            params['state'] = state

        # Note: Actual OAuth URL would be specific to Lightspeed's implementation
        base_url = "https://cloud.lightspeedapp.com/oauth/authorize.php"
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])

        return f"{base_url}?{query_string}"

    def exchange_code_for_token(self, code: str, state: str | None = None) -> dict[str, Any]:
        """Exchange authorization code for access token."""
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise ValueError("OAuth not configured")

        token_url = "https://cloud.lightspeedapp.com/oauth/access_token.php"

        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri
        }

        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()

            token_data = response.json()

            # Store the tokens
            self.api_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')

            # Calculate expiry time
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            return token_data

        except requests.exceptions.RequestException as e:
            raise Exception(f"Token exchange failed: {e}")

    def refresh_access_token(self) -> dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise ValueError("Refresh token or OAuth credentials not available")

        token_url = "https://cloud.lightspeedapp.com/oauth/access_token.php"

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()

            token_data = response.json()

            # Update tokens
            self.api_token = token_data.get('access_token')
            if token_data.get('refresh_token'):
                self.refresh_token = token_data.get('refresh_token')

            # Calculate expiry time
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            return token_data

        except requests.exceptions.RequestException as e:
            raise Exception(f"Token refresh failed: {e}")

    def get_valid_token(self) -> str | None:
        """Get a valid access token, refreshing if necessary."""
        if self.is_token_valid():
            return self.api_token

        if self.refresh_token:
            try:
                self.refresh_access_token()
                return self.api_token
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                return None

        return None

    def revoke_token(self) -> bool:
        """Revoke the current access token."""
        if not self.api_token:
            return True

        # Note: Actual revocation URL would be specific to Lightspeed's implementation
        revoke_url = "https://cloud.lightspeedapp.com/oauth/revoke.php"

        try:
            requests.post(revoke_url, data={
                'token': self.api_token,
                'token_type_hint': 'access_token'
            })

            # Clear stored tokens
            self.api_token = None
            self.refresh_token = None
            self.token_expires_at = None

            return True

        except requests.exceptions.RequestException as e:
            print(f"Token revocation failed: {e}")
            return False

    def get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers for API requests."""
        token = self.get_valid_token()
        if not token:
            return {}

        return {
            'Authorization': f'{self.token_type} {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
