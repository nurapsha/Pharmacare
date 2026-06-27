from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'


class Medicine(models.Model):
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    manufacturer = models.CharField(max_length=200)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=10)
    expiry_date = models.DateField()
    batch_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity < self.minimum_stock

    @property
    def is_expiring_soon(self):
        return self.expiry_date <= (timezone.now().date() + timedelta(days=30))

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def days_until_expiry(self):
        delta = self.expiry_date - timezone.now().date()
        return delta.days

    @property
    def profit_margin(self):
        if self.cost_price > 0:
            return float(self.price - self.cost_price)
        return 0

    class Meta:
        ordering = ['name']


class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_purchases(self):
        return self.sale_set.aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0

    class Meta:
        ordering = ['name']


class Sale(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sale_date = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    invoice_number = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"Invoice #{self.invoice_number}"

    @property
    def net_total(self):
        return float(self.total_amount) - float(self.discount)

    @property
    def change_amount(self):
        return float(self.paid_amount) - self.net_total

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last = Sale.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m')}-{next_id:04d}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-sale_date']


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity}"

    @property
    def subtotal(self):
        return float(self.unit_price) * self.quantity

    @property
    def profit(self):
        return (float(self.unit_price) - float(self.medicine.cost_price)) * self.quantity


class StockLog(models.Model):
    """Tracks every stock change for audit purposes."""
    ACTION_CHOICES = [
        ('ADD', 'Stock Added'),
        ('SALE', 'Sold'),
        ('ADJUST', 'Manual Adjustment'),
        ('RETURN', 'Return'),
    ]
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    quantity_change = models.IntegerField()  # positive = added, negative = removed
    quantity_after = models.IntegerField()
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.medicine.name} | {self.action} | {self.quantity_change}"

    class Meta:
        ordering = ['-timestamp']
