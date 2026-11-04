
from django.core.management.base import BaseCommand

from orders.services.expiration_service import expire_pending_orders


class Command(BaseCommand):
    help = "Expire unpaid orders and release eligible inventory."

    def handle(self, *args, **options):
        result = expire_pending_orders()

        self.stdout.write(
            self.style.SUCCESS(
                f"Checked: {result['checked']} | "
                f"Released: {result['released']} | "
                f"Skipped: {result['skipped']}"
            )
        )
