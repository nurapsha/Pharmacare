from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Medicines
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicines/add/', views.medicine_add, name='medicine_add'),
    path('medicines/<int:pk>/', views.medicine_detail, name='medicine_detail'),
    path('medicines/<int:pk>/edit/', views.medicine_edit, name='medicine_edit'),
    path('medicines/<int:pk>/delete/', views.medicine_delete, name='medicine_delete'),
    path('medicines/<int:pk>/stock/', views.medicine_stock_adjust, name='medicine_stock_adjust'),

    # Inventory
    path('inventory/', views.inventory, name='inventory'),

    # Billing
    path('billing/', views.billing, name='billing'),
    path('billing/create/', views.create_sale, name='create_sale'),
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/<int:pk>/receipt/', views.sale_receipt, name='sale_receipt'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_add, name='customer_add'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_add, name='supplier_add'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),

    # Reports
    path('reports/', views.reports, name='reports'),

    #AI Insights
    

    # API
    path('api/medicines/search/', views.api_medicine_search, name='api_medicine_search'),
]
