from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('waiter', 'Waiter'),
        ('chef', 'Chef'),
        ('admin', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='waiter')

    def __str__(self):
        return f"{self.user.username} — {self.role}"

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)


class Table(models.Model):
    number = models.IntegerField(unique=True)
    is_occupied = models.BooleanField(default=False)

    def __str__(self):
        return f"Table {self.number}"


class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Food'),
        ('drink', 'Drink'),
        ('dessert', 'Dessert'),
    ]
    FOOD_TYPE_CHOICES = [
        ('veg',     'Vegetarian'),
        ('non_veg', 'Non-Vegetarian'),
        ('na',      'N/A'),
    ]
    name         = models.CharField(max_length=100)
    price        = models.DecimalField(max_digits=6, decimal_places=2)
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    food_type    = models.CharField(max_length=10, choices=FOOD_TYPE_CHOICES, default='na')
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (${self.price})"


from django.utils import timezone

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('served', 'Served'),
        ('paid', 'Paid'),
    ]
    table              = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders')
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)
    served_at          = models.DateTimeField(null=True, blank=True)
    daily_order_number = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            from django.utils import timezone
            today = timezone.now().date()
            last = Order.objects.filter(
                created_at__date=today
            ).order_by('-daily_order_number').first()
            self.daily_order_number = (last.daily_order_number + 1) if last else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.daily_order_number} - Table {self.table.number} [{self.status}]"

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())
class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item  = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity   = models.PositiveIntegerField(default=1)
    note       = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if self.unit_price == 0 or self.unit_price is None:
            self.unit_price = self.menu_item.price
        super().save(*args, **kwargs)

    def subtotal(self):
        return self.quantity * self.unit_price
    
class RolePermission(models.Model):
    can_add_menu    = models.BooleanField(default=False)
    can_edit_menu   = models.BooleanField(default=False)
    can_delete_menu = models.BooleanField(default=False)
    can_add_table   = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Waiter Permissions'

    def __str__(self):
        return 'Waiter Permissions'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj