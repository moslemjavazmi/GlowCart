
from django.core.management.base import BaseCommand

from payments.services.reconciliation_service import (
    reconcile_unresolved_payments,
)


class Command(BaseCommand):
    help = "Reconcile unresolved payments with payment gateways."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of payments to process.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        result = reconcile_unresolved_payments(
            limit=limit
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Checked: {result['checked']}"
            )
        )

        for item in result["results"]:
            self.stdout.write(str(item))
