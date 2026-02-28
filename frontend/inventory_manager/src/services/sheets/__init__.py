"""
Sheets service package.

This __init__ provides compatibility for legacy import paths used in tests:
 - from services.sheets import SheetsService
 - patch('services.sheets.gspread') / patch('services.sheets.Credentials')
"""

import gspread  # re-exported for test patching paths
from google.oauth2.service_account import Credentials  # re-exported for test patching paths

from .service import SheetsService

__all__ = ["SheetsService", "gspread", "Credentials"]

