from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User

DEMO_USERS = [
    {"email": "admin@finpilot.local", "role": User.Role.ADMIN, "first_name": "Demo", "last_name": "Admin"},
    {"email": "viewer@finpilot.local", "role": User.Role.VIEWER, "first_name": "Demo", "last_name": "Viewer"},
]


class Command(BaseCommand):
    help = "Create (or reset) the demo ADMIN and VIEWER accounts. Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="FinPilot@2026", help="Password for both demo users")

    @transaction.atomic
    def handle(self, *args, password, **options):
        for data in DEMO_USERS:
            user, created = User.objects.update_or_create(
                email=data["email"],
                defaults={k: v for k, v in data.items() if k != "email"} | {"is_active": True},
            )
            user.set_password(password)
            user.save(update_fields=["password"])
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} {user.role:<6} {user.email}"))
