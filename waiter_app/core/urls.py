from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('access-denied/', views.access_denied, name='access_denied'),

    # Waiter
    path('dashboard/', views.dashboard, name='dashboard'),
    path('table/<int:table_id>/', views.table_order, name='table_order'),
    path('order/remove/<int:item_id>/', views.remove_order_item, name='remove_order_item'),
    path('order/serve/<int:order_id>/', views.mark_order_served, name='mark_order_served'),
    path('order/<int:order_id>/bill/', views.bill, name='bill'),
    path('order/<int:order_id>/paid/', views.mark_paid, name='mark_paid'),

    # Kitchen
    path('kitchen/', views.kitchen, name='kitchen'),
    path('order/<int:order_id>/status/', views.update_order_status, name='update_order_status'),

    # Admin
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/create/', views.admin_create_user, name='admin_create_user'),
    path('admin-panel/users/<int:user_id>/edit/', views.admin_edit_user, name='admin_edit_user'),
    path('admin-panel/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin-panel/menu/', views.admin_menu, name='admin_menu'),
    path('admin-panel/menu/create/', views.admin_create_menu_item, name='admin_create_menu_item'),
    path('admin-panel/menu/<int:item_id>/edit/', views.admin_edit_menu_item, name='admin_edit_menu_item'),
    path('admin-panel/menu/<int:item_id>/delete/', views.admin_delete_menu_item, name='admin_delete_menu_item'),
    path('admin-panel/tables/', views.admin_tables, name='admin_tables'),
    path('admin-panel/tables/create/', views.admin_create_table, name='admin_create_table'),
    path('admin-panel/tables/<int:table_id>/delete/', views.admin_delete_table, name='admin_delete_table'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('admin-panel/permissions/', views.admin_permissions, name='admin_permissions'),
    path('api/dashboard/', views.api_dashboard_status, name='api_dashboard'),    # API for real-time
    path('api/kitchen/', views.api_kitchen_status, name='api_kitchen'),
]