"""
AI Engine for Pharmacy Management System
Uses simple statistical analysis and pandas for predictions.
No complex ML — beginner-friendly logic.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F
import json


def get_date_range(days=30):
    end = timezone.now().date()
    start = end - timedelta(days=days)
    return start, end


# ─────────────────────────────────────────────
# 1. DEMAND PREDICTION
# Calculates average daily sales and predicts
# how much stock will be needed in next 30 days.
# ─────────────────────────────────────────────
def demand_prediction(days=30):
    from .models import SaleItem, Medicine

    start, end = get_date_range(days)

    # Total sold per medicine in the window
    sales_data = (
        SaleItem.objects
        .filter(sale__sale_date__date__range=[start, end])
        .values('medicine__id', 'medicine__name', 'medicine__quantity')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')
    )

    predictions = []
    for item in sales_data:
        avg_daily = item['total_sold'] / days
        predicted_30 = round(avg_daily * 30)
        current_stock = item['medicine__quantity']
        needed = max(0, predicted_30 - current_stock)

        status = 'OK'
        if needed > 0:
            status = 'RESTOCK'
        elif current_stock < avg_daily * 7:
            status = 'LOW'

        predictions.append({
            'medicine_id': item['medicine__id'],
            'medicine_name': item['medicine__name'],
            'current_stock': current_stock,
            'sold_in_period': item['total_sold'],
            'avg_daily_sales': round(avg_daily, 2),
            'predicted_need_30d': predicted_30,
            'restock_needed': needed,
            'status': status,
            'suggestion': (
                f"Increase stock by {needed} units to cover next 30 days."
                if needed > 0
                else "Stock level is adequate."
            ),
        })

    return predictions


# ─────────────────────────────────────────────
# 2. EXPIRY RISK PREDICTION
# Finds medicines that are near expiry AND
# have low sales — risk of waste.
# ─────────────────────────────────────────────
def expiry_risk_prediction():
    from .models import Medicine, SaleItem

    today = timezone.now().date()
    soon = today + timedelta(days=60)

    at_risk = Medicine.objects.filter(
        expiry_date__lte=soon,
        expiry_date__gte=today,
        quantity__gt=0
    )

    start_30, _ = get_date_range(30)
    result = []

    for med in at_risk:
        sold_30d = SaleItem.objects.filter(
            medicine=med,
            sale__sale_date__date__gte=start_30
        ).aggregate(total=Sum('quantity'))['total'] or 0

        days_left = (med.expiry_date - today).days
        avg_daily = sold_30d / 30
        will_sell = round(avg_daily * days_left)
        waste_risk = max(0, med.quantity - will_sell)

        risk_level = 'LOW'
        if days_left <= 15:
            risk_level = 'CRITICAL'
        elif days_left <= 30:
            risk_level = 'HIGH'
        elif waste_risk > 10:
            risk_level = 'MEDIUM'

        suggestion = ''
        if risk_level in ['CRITICAL', 'HIGH']:
            discount_pct = 30 if risk_level == 'CRITICAL' else 15
            suggestion = (
                f"Apply {discount_pct}% discount immediately. "
                f"Only {days_left} days left. Est. {waste_risk} units may expire."
            )
        elif risk_level == 'MEDIUM':
            suggestion = (
                f"Consider a 10% promotion. "
                f"~{waste_risk} units at risk of expiry in {days_left} days."
            )
        else:
            suggestion = f"Monitor closely. {days_left} days remaining."

        result.append({
            'medicine_id': med.id,
            'medicine_name': med.name,
            'expiry_date': med.expiry_date.strftime('%Y-%m-%d'),
            'days_left': days_left,
            'current_stock': med.quantity,
            'sold_30d': sold_30d,
            'estimated_will_sell': will_sell,
            'waste_risk_units': waste_risk,
            'risk_level': risk_level,
            'suggestion': suggestion,
        })

    # Sort by most urgent
    result.sort(key=lambda x: x['days_left'])
    return result


# ─────────────────────────────────────────────
# 3. SMART SALES ANALYSIS
# Top/least sellers, best sales day, trends.
# ─────────────────────────────────────────────
def smart_sales_analysis(days=30):
    from .models import SaleItem, Sale

    start, end = get_date_range(days)

    # Top selling medicines
    top_medicines = (
        SaleItem.objects
        .filter(sale__sale_date__date__range=[start, end])
        .values('medicine__name')
        .annotate(total_qty=Sum('quantity'), total_revenue=Sum(F('quantity') * F('unit_price')))
        .order_by('-total_qty')[:10]
    )

    # Least selling medicines (among those that had at least 1 sale)
    least_medicines = (
        SaleItem.objects
        .filter(sale__sale_date__date__range=[start, end])
        .values('medicine__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('total_qty')[:5]
    )

    # Best sales day of week
    from django.db.models.functions import ExtractWeekDay
    day_sales = (
        Sale.objects
        .filter(sale_date__date__range=[start, end])
        .annotate(weekday=ExtractWeekDay('sale_date'))
        .values('weekday')
        .annotate(count=Count('id'), revenue=Sum('total_amount'))
        .order_by('-revenue')
    )

    day_names = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday',
                 4: 'Wednesday', 5: 'Thursday', 6: 'Friday', 7: 'Saturday'}

    best_day = None
    if day_sales:
        best = day_sales[0]
        best_day = {
            'day': day_names.get(best['weekday'], 'Unknown'),
            'count': best['count'],
            'revenue': float(best['revenue'] or 0),
        }

    # Daily revenue trend for chart
    from django.db.models.functions import TruncDate
    daily_trend = (
        Sale.objects
        .filter(sale_date__date__range=[start, end])
        .annotate(date=TruncDate('sale_date'))
        .values('date')
        .annotate(revenue=Sum('total_amount'), count=Count('id'))
        .order_by('date')
    )

    trend_labels = [str(d['date']) for d in daily_trend]
    trend_revenue = [float(d['revenue'] or 0) for d in daily_trend]

    return {
        'top_medicines': list(top_medicines),
        'least_medicines': list(least_medicines),
        'best_day': best_day,
        'trend_labels': json.dumps(trend_labels),
        'trend_revenue': json.dumps(trend_revenue),
        'period_days': days,
    }


# ─────────────────────────────────────────────
# 4. STOCK-OUT WARNING
# Predicts how many days until each medicine
# runs out based on average daily sales.
# ─────────────────────────────────────────────
def stockout_warning():
    from .models import Medicine, SaleItem

    start, _ = get_date_range(14)  # Use last 14 days for recent trend
    warnings = []

    medicines = Medicine.objects.filter(quantity__gt=0)

    for med in medicines:
        sold_14d = SaleItem.objects.filter(
            medicine=med,
            sale__sale_date__date__gte=start
        ).aggregate(total=Sum('quantity'))['total'] or 0

        if sold_14d == 0:
            continue  # Not selling, skip

        avg_daily = sold_14d / 14
        days_left = round(med.quantity / avg_daily) if avg_daily > 0 else 999

        if days_left <= 30:
            urgency = 'CRITICAL' if days_left <= 3 else ('HIGH' if days_left <= 7 else 'MEDIUM')
            warnings.append({
                'medicine_id': med.id,
                'medicine_name': med.name,
                'current_stock': med.quantity,
                'avg_daily_sales': round(avg_daily, 1),
                'days_until_stockout': days_left,
                'urgency': urgency,
                'message': (
                    f"⚠️ Will run out in ~{days_left} day{'s' if days_left != 1 else ''}! "
                    f"Order at least {round(avg_daily * 30)} units."
                ),
            })

    warnings.sort(key=lambda x: x['days_until_stockout'])
    return warnings


# ─────────────────────────────────────────────
# 5. DASHBOARD SUMMARY STATS
# Quick numbers for the main dashboard.
# ─────────────────────────────────────────────
def dashboard_stats():
    from .models import Medicine, Sale, Customer, SaleItem

    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_medicines = Medicine.objects.count()
    low_stock_count = Medicine.objects.filter(quantity__lt=F('minimum_stock')).count()
    expiring_soon = Medicine.objects.filter(
        expiry_date__lte=today + timedelta(days=30),
        expiry_date__gte=today
    ).count()
    expired_count = Medicine.objects.filter(expiry_date__lt=today).count()

    today_sales = Sale.objects.filter(sale_date__date=today)
    today_revenue = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    today_count = today_sales.count()

    month_sales = Sale.objects.filter(sale_date__date__gte=month_start)
    month_revenue = month_sales.aggregate(total=Sum('total_amount'))['total'] or 0

    # Profit = sum of (unit_price - cost_price) * qty
    month_profit = (
        SaleItem.objects
        .filter(sale__sale_date__date__gte=month_start)
        .aggregate(
            profit=Sum(
                (F('unit_price') - F('medicine__cost_price')) * F('quantity')
            )
        )['profit'] or 0
    )

    total_customers = Customer.objects.count()

    return {
        'total_medicines': total_medicines,
        'low_stock_count': low_stock_count,
        'expiring_soon': expiring_soon,
        'expired_count': expired_count,
        'today_revenue': float(today_revenue),
        'today_count': today_count,
        'month_revenue': float(month_revenue),
        'month_profit': float(month_profit),
        'total_customers': total_customers,
        'ai_warnings': len(stockout_warning()),
    }
