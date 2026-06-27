from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
import json

from .models import Medicine, Customer, Supplier, Sale, SaleItem, StockLog, Category
from .forms import MedicineForm, CustomerForm, SupplierForm, SaleCreateForm, StockAdjustForm
from . import ai_engine


# ══════════════════════════════════════════
# AUTH VIEWS
# ══════════════════════════════════════════

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('login')


# ══════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════

@login_required
def dashboard(request):
    stats = ai_engine.dashboard_stats()
    recent_sales = Sale.objects.select_related('customer', 'staff').order_by('-sale_date')[:5]
    low_stock = Medicine.objects.filter(quantity__lt=F('minimum_stock'))[:5]
    expiring = Medicine.objects.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=30),
        expiry_date__gte=timezone.now().date()
    ).order_by('expiry_date')[:5]

    # Mini chart data: last 7 days revenue
    labels, revenues = [], []
    for i in range(6, -1, -1):
        d = timezone.now().date() - timedelta(days=i)
        rev = Sale.objects.filter(sale_date__date=d).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        labels.append(d.strftime('%b %d'))
        revenues.append(float(rev))

    context = {
        **stats,
        'recent_sales': recent_sales,
        'low_stock': low_stock,
        'expiring': expiring,
        'chart_labels': json.dumps(labels),
        'chart_revenues': json.dumps(revenues),
    }
    return render(request, 'core/dashboard.html', context)


# ══════════════════════════════════════════
# MEDICINE VIEWS
# ══════════════════════════════════════════

@login_required
def medicine_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    filter_type = request.GET.get('filter', '')

    medicines = Medicine.objects.select_related('category', 'supplier').all()

    if query:
        medicines = medicines.filter(
            Q(name__icontains=query) |
            Q(generic_name__icontains=query) |
            Q(manufacturer__icontains=query)
        )
    if category_id:
        medicines = medicines.filter(category_id=category_id)
    if filter_type == 'low_stock':
        medicines = medicines.filter(quantity__lt=F('minimum_stock'))
    elif filter_type == 'expiring':
        medicines = medicines.filter(
            expiry_date__lte=timezone.now().date() + timedelta(days=30)
        )
    elif filter_type == 'expired':
        medicines = medicines.filter(expiry_date__lt=timezone.now().date())

    categories = Category.objects.all()

    context = {
        'medicines': medicines,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'filter_type': filter_type,
    }
    return render(request, 'core/medicine_list.html', context)


@login_required
def medicine_add(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            medicine = form.save()
            StockLog.objects.create(
                medicine=medicine,
                action='ADD',
                quantity_change=medicine.quantity,
                quantity_after=medicine.quantity,
                notes='Initial stock entry',
                performed_by=request.user
            )
            messages.success(request, f'Medicine "{medicine.name}" added successfully.')
            return redirect('medicine_list')
    else:
        form = MedicineForm()
    return render(request, 'core/medicine_form.html', {'form': form, 'title': 'Add Medicine'})


@login_required
def medicine_edit(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    old_qty = medicine.quantity

    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            updated = form.save()
            if updated.quantity != old_qty:
                StockLog.objects.create(
                    medicine=updated,
                    action='ADJUST',
                    quantity_change=updated.quantity - old_qty,
                    quantity_after=updated.quantity,
                    notes='Manual edit',
                    performed_by=request.user
                )
            messages.success(request, f'Medicine "{updated.name}" updated.')
            return redirect('medicine_list')
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'core/medicine_form.html', {'form': form, 'title': 'Edit Medicine', 'medicine': medicine})


@login_required
def medicine_delete(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        name = medicine.name
        medicine.delete()
        messages.success(request, f'Medicine "{name}" deleted.')
        return redirect('medicine_list')
    return render(request, 'core/medicine_confirm_delete.html', {'medicine': medicine})


@login_required
def medicine_detail(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    stock_logs = StockLog.objects.filter(medicine=medicine)[:10]
    sale_items = SaleItem.objects.filter(medicine=medicine).select_related('sale')[:10]
    context = {'medicine': medicine, 'stock_logs': stock_logs, 'sale_items': sale_items}
    return render(request, 'core/medicine_detail.html', context)


@login_required
def medicine_stock_adjust(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = StockAdjustForm(request.POST)
        if form.is_valid():
            qty = form.cleaned_data['quantity_to_add']
            notes = form.cleaned_data['notes']
            medicine.quantity += qty
            medicine.save()
            StockLog.objects.create(
                medicine=medicine,
                action='ADD',
                quantity_change=qty,
                quantity_after=medicine.quantity,
                notes=notes or 'Stock restocked',
                performed_by=request.user
            )
            messages.success(request, f'Added {qty} units to {medicine.name}.')
            return redirect('medicine_detail', pk=pk)
    else:
        form = StockAdjustForm()
    return render(request, 'core/stock_adjust.html', {'medicine': medicine, 'form': form})


# ══════════════════════════════════════════
# INVENTORY VIEW
# ══════════════════════════════════════════

@login_required
def inventory(request):
    today = timezone.now().date()
    low_stock = Medicine.objects.filter(quantity__lt=F('minimum_stock'))
    expiring = Medicine.objects.filter(
        expiry_date__lte=today + timedelta(days=30),
        expiry_date__gte=today
    ).order_by('expiry_date')
    expired = Medicine.objects.filter(expiry_date__lt=today)
    all_medicines = Medicine.objects.all().order_by('name')

    context = {
        'low_stock': low_stock,
        'expiring': expiring,
        'expired': expired,
        'all_medicines': all_medicines,
        'low_stock_count': low_stock.count(),
        'expiring_count': expiring.count(),
        'expired_count': expired.count(),
    }
    return render(request, 'core/inventory.html', context)


# ══════════════════════════════════════════
# BILLING / SALES VIEWS
# ══════════════════════════════════════════

@login_required
def billing(request):
    medicines = Medicine.objects.filter(quantity__gt=0).order_by('name')
    customers = Customer.objects.all().order_by('name')
    form = SaleCreateForm()
    return render(request, 'core/billing.html', {
        'medicines': medicines,
        'customers': customers,
        'form': form,
    })


@login_required
def create_sale(request):
    """Handles the actual sale POST — creates Sale and SaleItem records."""
    if request.method != 'POST':
        return redirect('billing')

    medicine_ids = request.POST.getlist('medicine_id[]')
    quantities = request.POST.getlist('quantity[]')
    customer_id = request.POST.get('customer')
    discount = request.POST.get('discount', 0) or 0
    paid_amount = request.POST.get('paid_amount', 0) or 0
    notes = request.POST.get('notes', '')

    if not medicine_ids:
        messages.error(request, 'Please add at least one medicine to the bill.')
        return redirect('billing')

    # Validate stock availability
    errors = []
    items_data = []
    total = 0

    for med_id, qty_str in zip(medicine_ids, quantities):
        try:
            qty = int(qty_str)
            med = Medicine.objects.get(pk=med_id)
            if qty > med.quantity:
                errors.append(f'Insufficient stock for {med.name} (available: {med.quantity})')
            else:
                subtotal = float(med.price) * qty
                total += subtotal
                items_data.append({'medicine': med, 'qty': qty, 'price': med.price})
        except (Medicine.DoesNotExist, ValueError):
            errors.append(f'Invalid medicine or quantity.')

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect('billing')

    # Create the sale
    customer = None
    if customer_id:
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            pass

    sale = Sale.objects.create(
        customer=customer,
        staff=request.user,
        total_amount=total,
        discount=float(discount),
        paid_amount=float(paid_amount),
        notes=notes,
        invoice_number=''  # auto-generated in save()
    )

    # Create sale items and deduct stock
    for item in items_data:
        SaleItem.objects.create(
            sale=sale,
            medicine=item['medicine'],
            quantity=item['qty'],
            unit_price=item['price']
        )
        item['medicine'].quantity -= item['qty']
        item['medicine'].save()
        StockLog.objects.create(
            medicine=item['medicine'],
            action='SALE',
            quantity_change=-item['qty'],
            quantity_after=item['medicine'].quantity,
            notes=f'Sale Invoice {sale.invoice_number}',
            performed_by=request.user
        )

    messages.success(request, f'Sale recorded! Invoice: {sale.invoice_number}')
    return redirect('sale_receipt', pk=sale.pk)


@login_required
def sale_receipt(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.select_related('medicine').all()
    return render(request, 'core/sale_receipt.html', {'sale': sale, 'items': items})


@login_required
def sales_list(request):
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    sales = Sale.objects.select_related('customer', 'staff').all()

    if start_date:
        sales = sales.filter(sale_date__date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__date__lte=end_date)

    total_revenue = sales.aggregate(t=Sum('total_amount'))['t'] or 0
    context = {'sales': sales, 'total_revenue': total_revenue, 'start_date': start_date, 'end_date': end_date}
    return render(request, 'core/sales_list.html', context)


# ══════════════════════════════════════════
# CUSTOMER VIEWS
# ══════════════════════════════════════════

@login_required
def customer_list(request):
    query = request.GET.get('q', '')
    customers = Customer.objects.all()
    if query:
        customers = customers.filter(Q(name__icontains=query) | Q(phone__icontains=query))
    return render(request, 'core/customer_list.html', {'customers': customers, 'query': query})


@login_required
def customer_add(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" added.')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'core/customer_form.html', {'form': form, 'title': 'Add Customer'})


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated.')
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'core/customer_form.html', {'form': form, 'title': 'Edit Customer'})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    sales = Sale.objects.filter(customer=customer).prefetch_related('items__medicine')
    total_spent = sales.aggregate(t=Sum('total_amount'))['t'] or 0
    return render(request, 'core/customer_detail.html', {
        'customer': customer,
        'sales': sales,
        'total_spent': total_spent,
    })


# ══════════════════════════════════════════
# SUPPLIER VIEWS
# ══════════════════════════════════════════

@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'core/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_add(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            s = form.save()
            messages.success(request, f'Supplier "{s.name}" added.')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'core/supplier_form.html', {'form': form, 'title': 'Add Supplier'})


@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated.')
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'core/supplier_form.html', {'form': form, 'title': 'Edit Supplier'})


@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    medicines = Medicine.objects.filter(supplier=supplier)
    return render(request, 'core/supplier_detail.html', {'supplier': supplier, 'medicines': medicines})


# ══════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════

@login_required
def reports(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Daily stats
    today_sales = Sale.objects.filter(sale_date__date=today)
    today_revenue = today_sales.aggregate(t=Sum('total_amount'))['t'] or 0

    # Monthly stats
    month_sales = Sale.objects.filter(sale_date__date__gte=month_start)
    month_revenue = month_sales.aggregate(t=Sum('total_amount'))['t'] or 0
    month_profit = SaleItem.objects.filter(
        sale__sale_date__date__gte=month_start
    ).aggregate(
        p=Sum((F('unit_price') - F('medicine__cost_price')) * F('quantity'))
    )['p'] or 0

    # Monthly chart: last 6 months
    month_labels, month_revenues = [], []
    for i in range(5, -1, -1):
        d = today - timedelta(days=30 * i)
        ms = d.replace(day=1)
        me = (ms + timedelta(days=32)).replace(day=1)
        rev = Sale.objects.filter(
            sale_date__date__gte=ms,
            sale_date__date__lt=me
        ).aggregate(t=Sum('total_amount'))['t'] or 0
        month_labels.append(ms.strftime('%b %Y'))
        month_revenues.append(float(rev))

    # Top medicines this month
    top_meds = (
        SaleItem.objects
        .filter(sale__sale_date__date__gte=month_start)
        .values('medicine__name')
        .annotate(total_qty=Sum('quantity'), revenue=Sum(F('quantity') * F('unit_price')))
        .order_by('-revenue')[:10]
    )

    context = {
        'today': today,
        'today_revenue': float(today_revenue),
        'today_count': today_sales.count(),
        'month_revenue': float(month_revenue),
        'month_profit': float(month_profit),
        'month_count': month_sales.count(),
        'top_meds': top_meds,
        'month_labels': json.dumps(month_labels),
        'month_revenues': json.dumps(month_revenues),
    }
    return render(request, 'core/reports.html', context)


# ══════════════════════════════════════════
# AI INSIGHTS PAGE
# ══════════════════════════════════════════



# ══════════════════════════════════════════
# API: Medicine search for billing
# ══════════════════════════════════════════

@login_required
def api_medicine_search(request):
    q = request.GET.get('q', '')
    medicines = Medicine.objects.filter(
        Q(name__icontains=q) | Q(generic_name__icontains=q),
        quantity__gt=0
    )[:15]
    data = [
        {
            'id': m.id,
            'name': m.name,
            'price': float(m.price),
            'quantity': m.quantity,
            'generic': m.generic_name,
        }
        for m in medicines
    ]
    return JsonResponse({'medicines': data})
