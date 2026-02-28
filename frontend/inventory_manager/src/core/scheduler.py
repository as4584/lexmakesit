"""
APScheduler for automated inventory management jobs.
Handles hourly sync from Lightspeed and nightly maintenance tasks.
"""
import atexit
from datetime import datetime

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler


class InventoryScheduler:
    """Scheduler for automated inventory management tasks."""

    def __init__(self):
        """Initialize the scheduler with job stores and executors."""
        jobstores = {
            'default': MemoryJobStore()
        }

        executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }

        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5 minutes
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        self.is_running = False

    def start(self):
        """Start the scheduler and register all jobs."""
        if self.is_running:
            print("Scheduler is already running")
            return

        try:
            # Add scheduled jobs
            self._add_sync_job()
            self._add_maintenance_job()
            self._add_backup_job()

            # Start the scheduler
            self.scheduler.start()
            self.is_running = True

            # Ensure scheduler shuts down on app exit
            atexit.register(self.shutdown)

            print("Inventory scheduler started successfully")
            self._log_scheduled_jobs()

        except Exception as e:
            print(f"Failed to start scheduler: {e}")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print("Inventory scheduler stopped")

    def _add_sync_job(self):
        """Add hourly sync job from Lightspeed."""
        self.scheduler.add_job(
            func=self._sync_from_lightspeed,
            trigger='interval',
            hours=1,
            id='hourly_sync',
            name='Hourly Lightspeed Sync',
            replace_existing=True,
            next_run_time=datetime.now()  # Run immediately on start
        )

    def _add_maintenance_job(self):
        """Add nightly maintenance job for sorting and cleanup."""
        self.scheduler.add_job(
            func=self._nightly_maintenance,
            trigger='cron',
            hour=3,  # 3 AM UTC
            minute=0,
            id='nightly_maintenance',
            name='Nightly Maintenance',
            replace_existing=True
        )

    def _add_backup_job(self):
        """Add nightly backup job."""
        self.scheduler.add_job(
            func=self._create_backup,
            trigger='cron',
            hour=2,  # 2 AM UTC
            minute=30,
            id='nightly_backup',
            name='Nightly Backup',
            replace_existing=True
        )

    def _sync_from_lightspeed(self):
        """Hourly sync job from Lightspeed to Google Sheets."""
        try:
            print(f"[{datetime.now()}] Starting hourly sync from Lightspeed...")

            # Import services here to avoid circular imports
            from services.inventory import InventoryService
            from services.ls_api import LightspeedAPI
            from services.sheets import SheetsService

            # Initialize services
            ls_api = LightspeedAPI()
            sheets_service = SheetsService()
            inventory_service = InventoryService(sheets_service)

            # Perform full sync
            sync_result = ls_api.sync_from_ls()

            if 'error' in sync_result:
                print(f"Sync failed: {sync_result['error']}")
                return

            # Convert Lightspeed data to inventory format
            inventory_data = self._convert_ls_to_inventory(sync_result)

            # Sort the data
            sorted_inventory = inventory_service.auto_sort(inventory_data)

            # Update Google Sheets
            if sheets_service.update_inventory_data(sorted_inventory):
                print(f"Hourly sync completed successfully: {len(sorted_inventory)} items updated")

                # Update low stock list
                low_stock_df = inventory_service.low_stock(sorted_inventory)
                sheets_service.update_restock_list(low_stock_df)

            else:
                print("Failed to update Google Sheets")

        except Exception as e:
            print(f"Hourly sync error: {e}")

    def _nightly_maintenance(self):
        """Nightly maintenance job for data sorting and cleanup."""
        try:
            print(f"[{datetime.now()}] Starting nightly maintenance...")

            from services.inventory import InventoryService
            from services.sheets import SheetsService

            sheets_service = SheetsService()
            inventory_service = InventoryService(sheets_service)

            # Get current inventory data
            inventory_df = sheets_service.get_inventory_data()

            if inventory_df.empty:
                print("No inventory data found for maintenance")
                return

            # Sort inventory data
            sorted_inventory = inventory_service.auto_sort(inventory_df)

            # Update sorted data back to sheets
            sheets_service.update_inventory_data(sorted_inventory)

            # Update low stock list
            low_stock_df = inventory_service.low_stock(sorted_inventory)
            sheets_service.update_restock_list(low_stock_df)

            print(f"Nightly maintenance completed: {len(sorted_inventory)} items sorted")

        except Exception as e:
            print(f"Nightly maintenance error: {e}")

    def _create_backup(self):
        """Nightly backup job for CSV export."""
        try:
            print(f"[{datetime.now()}] Creating nightly backup...")

            from services.sheets import SheetsService

            sheets_service = SheetsService()

            # Get current inventory data
            inventory_df = sheets_service.get_inventory_data()

            if inventory_df.empty:
                print("No inventory data found for backup")
                return

            # Create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"inventory_backup_{timestamp}.csv"

            if sheets_service.backup_to_csv(inventory_df, backup_filename):
                print(f"Backup created successfully: {backup_filename}")
            else:
                print("Backup creation failed")

        except Exception as e:
            print(f"Backup creation error: {e}")

    def _convert_ls_to_inventory(self, sync_result):
        """Convert Lightspeed sync result to inventory DataFrame format."""
        import pandas as pd

        inventory_records = []

        for product in sync_result.get('products', []):
            for variant in product.get('variants', []):
                record = {
                    'ItemID': variant.get('id'),
                    'SKU': variant.get('sku'),
                    'Name': variant.get('name'),
                    'Category': product.get('category', 'Unknown'),
                    'Color': variant.get('color', 'Unknown'),
                    'Size': variant.get('size', 'OS'),
                    'Barcode': variant.get('barcode', ''),
                    'RetailPrice': variant.get('retail_price', 0),
                    'QtyOnHand': variant.get('quantity_on_hand', 0),
                    'QtySold': 0,  # Will be updated by sales reconciliation
                    'Location': 'A1',  # Default location
                    'LastUpdated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                inventory_records.append(record)

        return pd.DataFrame(inventory_records)

    def _log_scheduled_jobs(self):
        """Log information about scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        print(f"Scheduled {len(jobs)} jobs:")

        for job in jobs:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S UTC') if job.next_run_time else 'None'
            print(f"  - {job.name} (ID: {job.id}): Next run at {next_run}")

    def get_job_status(self):
        """Get status of all scheduled jobs."""
        if not self.is_running:
            return {'status': 'stopped', 'jobs': []}

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })

        return {
            'status': 'running',
            'jobs': jobs,
            'job_count': len(jobs)
        }

    def trigger_sync_now(self):
        """Manually trigger a sync job."""
        if not self.is_running:
            return {'success': False, 'error': 'Scheduler not running'}

        try:
            self.scheduler.add_job(
                func=self._sync_from_lightspeed,
                trigger='date',
                run_date=datetime.now(),
                id='manual_sync',
                name='Manual Sync',
                replace_existing=True
            )
            return {'success': True, 'message': 'Manual sync triggered'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Global scheduler instance
scheduler_instance = None


def start_scheduler():
    """Start the global scheduler instance."""
    global scheduler_instance

    if scheduler_instance is None:
        scheduler_instance = InventoryScheduler()

    if not scheduler_instance.is_running:
        scheduler_instance.start()

    return scheduler_instance


def get_scheduler():
    """Get the global scheduler instance."""
    return scheduler_instance


def stop_scheduler():
    """Stop the global scheduler instance."""
    global scheduler_instance

    if scheduler_instance and scheduler_instance.is_running:
        scheduler_instance.shutdown()
        scheduler_instance = None
