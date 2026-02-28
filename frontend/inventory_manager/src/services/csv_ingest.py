"""
Compatibility shim to preserve legacy import path `services.csv_ingest`.
Re-exports CSVIngestService from `src.ingestion.csv_ingest`.
"""
from src.ingestion.csv_ingest import CSVIngestService

__all__ = ["CSVIngestService"]
