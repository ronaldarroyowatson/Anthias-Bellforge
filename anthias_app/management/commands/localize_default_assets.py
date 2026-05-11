# Ensure persisted default widget URIs are localized for this device.

from django.core.management.base import BaseCommand

from anthias_app.helpers import localize_existing_default_assets


class Command(BaseCommand):
    help = 'Localize persisted default widget assets for this device.'

    def handle(self, *args, **options):
        updated_count = localize_existing_default_assets()
        self.stdout.write(
            self.style.SUCCESS(
                f'Localized default assets updated: {updated_count}'
            )
        )
