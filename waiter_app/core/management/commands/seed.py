from django.core.management.base import BaseCommand
from core.models import Table, MenuItem

class Command(BaseCommand):
    help = 'Seed initial tables and menu items'

    def handle(self, *args, **kwargs):
        for i in range(1, 6):
            Table.objects.get_or_create(number=i)

        items = [
            ('Burger',    8.99,  'food'),
            ('Pizza',     11.99, 'food'),
            ('Pasta',     9.99,  'food'),
            ('Coke',      1.99,  'drink'),
            ('Water',     0.99,  'drink'),
            ('Ice Cream', 3.99,  'dessert'),
        ]
        for name, price, category in items:
            MenuItem.objects.get_or_create(
                name=name,
                defaults={'price': price, 'category': category, 'is_available': True}
            )

        self.stdout.write(self.style.SUCCESS('✅ Seeded tables and menu items!'))