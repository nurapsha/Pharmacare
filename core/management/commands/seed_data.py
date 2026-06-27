"""
Seed command: populates the database with realistic sample data
for demonstration purposes.
Run: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
import random

from core.models import (
    Category, Supplier, Medicine, Customer, Sale, SaleItem, StockLog
)


class Command(BaseCommand):
    help = 'Seeds the database with sample pharmacy data'

    def handle(self, *args, **kwargs):
        self.stdout.write('🌱 Seeding database...')

        # Admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@pharmacy.com', 'admin123')
            admin.first_name = 'Admin'
            admin.last_name = 'User'
            admin.save()
            self.stdout.write('  ✓ Admin user created (admin / admin123)')

        # Staff user
        if not User.objects.filter(username='staff').exists():
            staff = User.objects.create_user('staff', 'staff@pharmacy.com', 'staff123')
            staff.first_name = 'Ram'
            staff.last_name = 'Sharma'
            staff.save()
            self.stdout.write('  ✓ Staff user created (staff / staff123)')

        # Categories
        categories = ['Antibiotics', 'Painkillers', 'Vitamins', 'Antacids',
                      'Antifungal', 'Antihistamine', 'Cardiovascular', 'Diabetes']
        cat_objs = {}
        for c in categories:
            obj, _ = Category.objects.get_or_create(name=c)
            cat_objs[c] = obj
        self.stdout.write('  ✓ Categories created')

        # Suppliers
        suppliers_data = [
            {'name': 'MediCorp Nepal', 'contact_person': 'Hari Bahadur', 'phone': '9801234567'},
            {'name': 'PharmaBridge Ltd', 'contact_person': 'Sita Rana', 'phone': '9807654321'},
            {'name': 'HealthPlus Distributors', 'contact_person': 'Krishna Thapa', 'phone': '9809876543'},
        ]
        supplier_objs = []
        for s in suppliers_data:
            obj, _ = Supplier.objects.get_or_create(name=s['name'], defaults=s)
            supplier_objs.append(obj)
        self.stdout.write('  ✓ Suppliers created')

        # Medicines
        today = date.today()
        medicines_data = [
            ('Paracetamol 500mg', 'Acetaminophen', 'Painkillers', 'Sun Pharma', 15.00, 8.00, 150, 20),
            ('Amoxicillin 250mg', 'Amoxicillin', 'Antibiotics', 'Cipla', 45.00, 25.00, 80, 15),
            ('Ibuprofen 400mg', 'Ibuprofen', 'Painkillers', 'Ranbaxy', 25.00, 12.00, 60, 10),
            ('Vitamin C 500mg', 'Ascorbic Acid', 'Vitamins', 'Himalaya', 30.00, 15.00, 200, 25),
            ('Omeprazole 20mg', 'Omeprazole', 'Antacids', 'Dr Reddy', 55.00, 30.00, 40, 10),
            ('Cetirizine 10mg', 'Cetirizine', 'Antihistamine', 'GSK', 20.00, 10.00, 100, 15),
            ('Metformin 500mg', 'Metformin', 'Diabetes', 'Zydus', 35.00, 18.00, 70, 12),
            ('Atorvastatin 10mg', 'Atorvastatin', 'Cardiovascular', 'Pfizer', 80.00, 45.00, 50, 10),
            ('Azithromycin 500mg', 'Azithromycin', 'Antibiotics', 'Cipla', 120.00, 65.00, 30, 8),
            ('Pantoprazole 40mg', 'Pantoprazole', 'Antacids', 'Hetero', 65.00, 35.00, 45, 10),
            ('Clonazepam 0.5mg', 'Clonazepam', 'Cardiovascular', 'Ranbaxy', 40.00, 22.00, 25, 8),
            ('Vitamin D3 1000IU', 'Cholecalciferol', 'Vitamins', 'Himalaya', 50.00, 28.00, 90, 15),
            ('Fluconazole 150mg', 'Fluconazole', 'Antifungal', 'Cipla', 75.00, 40.00, 20, 5),
            ('Aspirin 75mg', 'Aspirin', 'Cardiovascular', 'Bayer', 18.00, 9.00, 120, 20),
            ('Doxycycline 100mg', 'Doxycycline', 'Antibiotics', 'Sun Pharma', 90.00, 50.00, 8, 10),
        ]

        # Some with near expiry
        expiry_dates = [
            today + timedelta(days=365),
            today + timedelta(days=180),
            today + timedelta(days=730),
            today + timedelta(days=400),
            today + timedelta(days=15),   # expiring soon!
            today + timedelta(days=500),
            today + timedelta(days=300),
            today + timedelta(days=600),
            today + timedelta(days=20),   # expiring soon!
            today + timedelta(days=450),
            today + timedelta(days=90),
            today + timedelta(days=365),
            today + timedelta(days=200),
            today + timedelta(days=700),
            today + timedelta(days=100),
        ]

        med_objs = []
        for i, (name, generic, cat, mfr, price, cost, qty, min_stock) in enumerate(medicines_data):
            med, created = Medicine.objects.get_or_create(
                name=name,
                defaults={
                    'generic_name': generic,
                    'category': cat_objs.get(cat),
                    'manufacturer': mfr,
                    'supplier': random.choice(supplier_objs),
                    'price': price,
                    'cost_price': cost,
                    'quantity': qty,
                    'minimum_stock': min_stock,
                    'expiry_date': expiry_dates[i],
                    'batch_number': f'BCH-{2024+i}-{random.randint(100,999)}',
                }
            )
            med_objs.append(med)
        self.stdout.write('  ✓ Medicines created')

        # Customers
        customers_data = [
            ('Aarav Shrestha', '9841111111', 'aarav@gmail.com'),
            ('Priya Tamang', '9842222222', 'priya@gmail.com'),
            ('Bikash Rai', '9843333333', ''),
            ('Sunita Gurung', '9844444444', 'sunita@gmail.com'),
            ('Rajan Magar', '9845555555', ''),
            ('Anita Karki', '9846666666', 'anita@gmail.com'),
            ('Deepak Thapa', '9847777777', ''),
            ('Kavya Sharma', '9848888888', 'kavya@gmail.com'),
        ]
        cust_objs = []
        for name, phone, email in customers_data:
            c, _ = Customer.objects.get_or_create(name=name, defaults={'phone': phone, 'email': email})
            cust_objs.append(c)
        self.stdout.write('  ✓ Customers created')

        # Sales — create 60 days of history
        admin_user = User.objects.get(username='admin')
        staff_user = User.objects.get(username='staff')
        sale_count = 0

        for days_ago in range(60, 0, -1):
            sale_date = timezone.now() - timedelta(days=days_ago)
            # 1-4 sales per day
            for _ in range(random.randint(1, 4)):
                customer = random.choice(cust_objs + [None])
                items = random.sample(med_objs, random.randint(1, 3))

                sale = Sale(
                    customer=customer,
                    staff=random.choice([admin_user, staff_user]),
                    sale_date=sale_date,
                    discount=random.choice([0, 0, 0, 5, 10]),
                    invoice_number=''
                )
                sale.save()

                total = 0
                for med in items:
                    qty = random.randint(1, 5)
                    if med.quantity >= qty:
                        SaleItem.objects.create(
                            sale=sale,
                            medicine=med,
                            quantity=qty,
                            unit_price=med.price
                        )
                        total += float(med.price) * qty

                sale.total_amount = total
                sale.paid_amount = total - float(sale.discount)
                sale.save()
                sale_count += 1

        self.stdout.write(f'  ✓ {sale_count} sales created (60 days history)')
        self.stdout.write(self.style.SUCCESS('\n✅ Database seeded successfully!'))
        self.stdout.write('   Login: admin / admin123')
        self.stdout.write('   URL: http://127.0.0.1:8000')
