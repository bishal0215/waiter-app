from time import timezone

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Table, MenuItem, Order, OrderItem, UserProfile
from .decorators import role_required
from django.contrib.auth.models import User
from django.contrib import messages
from .decorators import role_required, permission_required

# ── Auth ────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return _redirect_by_role(user)
        else:
            from django.contrib.auth.forms import AuthenticationForm
            form = AuthenticationForm()
            form.errors['__all__'] = ['Invalid credentials.']
            return render(request, 'core/login.html', {'form': form})

    from django.contrib.auth.forms import AuthenticationForm
    return render(request, 'core/login.html', {'form': AuthenticationForm()})


def _redirect_by_role(user):
    try:
        role = user.profile.role
    except Exception:
        return redirect('login')
    if role == 'chef':
        return redirect('kitchen')
    elif role == 'admin':
        return redirect('dashboard')
    else:
        return redirect('dashboard')


def logout_view(request):
    logout(request)
    return redirect('login')


def access_denied(request):
    return render(request, 'core/access_denied.html')


# ── Waiter Views ─────────────────────────────────────────

@role_required('waiter', 'admin')
def dashboard(request):
    from .models import RolePermission
    tables = Table.objects.all().order_by('number')
    for table in tables:
        table.active_order = Order.objects.filter(
            table=table,
            status__in=['pending', 'preparing', 'served']
        ).prefetch_related('items__menu_item').first()

    active_tables = [t for t in tables if t.is_occupied]
    free_tables   = [t for t in tables if not t.is_occupied]
    ready_orders  = Order.objects.filter(status='served').select_related('table')

    context = {
        'active_tables':  active_tables,
        'free_tables':    free_tables,
        'ready_orders':   ready_orders,
        'total_tables':   tables.count(),
        'occupied_count': len(active_tables),
        'free_count':     len(free_tables),
        'ready_count':    ready_orders.count(),
        'pending_count':  Order.objects.filter(status='pending').count(),
        'waiter_perms':   RolePermission.get(),
        'stats': [
            ('Total Tables',   tables.count(),                                'primary'),
            ('Occupied',       len(active_tables),                            'warning'),
            ('Free',           len(free_tables),                              'success'),
            ('Ready to Serve', ready_orders.count(),                          'danger'),
            ('Pending Orders', Order.objects.filter(status='pending').count(),'secondary'),
        ],
    }
    return render(request, 'core/dashboard.html', context)


@role_required('waiter', 'admin')
def table_order(request, table_id):
    table      = get_object_or_404(Table, id=table_id)
    menu_items = MenuItem.objects.filter(is_available=True).order_by('category')
    order      = Order.objects.filter(
        table=table, status__in=['pending', 'preparing', 'served']
    ).prefetch_related('items__menu_item').first()
    error      = None

    if request.method == 'POST':
        has_items = any(
            int(request.POST.get(f'quantity_{item.id}', 0)) > 0
            for item in menu_items
        )

        if not has_items:
            error = 'Please select at least one item before placing an order.'
        else:
            if not order:
                order = Order.objects.create(table=table, status='pending')
                table.is_occupied = True
                table.save()

            for item in menu_items:
                quantity = int(request.POST.get(f'quantity_{item.id}', 0))
                note     = request.POST.get(f'note_{item.id}', '')
                if quantity > 0:
                    order_item, created = OrderItem.objects.get_or_create(
                        order=order, menu_item=item,
                        defaults={
                            'quantity':   quantity,
                            'note':       note,
                            'unit_price': item.price,
                        }
                    )
                    if not created:
                        order_item.quantity  += quantity
                        order_item.note       = note
                        order_item.unit_price = item.price
                        order_item.save()

            return redirect('table_order', table_id=table.id)

    return render(request, 'core/table_order.html', {
        'table':      table,
        'menu_items': menu_items,
        'order':      order,
        'error':      error,
    })


@role_required('waiter', 'admin')
def mark_order_served(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'paid'
    order.served_at = tz.now()
    order.save()
    order.table.is_occupied = False
    order.table.save()
    return redirect('dashboard')


@role_required('waiter', 'admin')
def remove_order_item(request, item_id):
    order_item = get_object_or_404(OrderItem, id=item_id)
    table_id = order_item.order.table.id
    order = order_item.order
    order_item.delete()
    if order.items.count() == 0:
        order.delete()
        order.table.is_occupied = False
        order.table.save()
    return redirect('table_order', table_id=table_id)

@role_required('waiter', 'admin')
def bill(request, order_id):
    order    = get_object_or_404(Order, id=order_id)
    items    = order.items.select_related('menu_item').all()
    subtotal = order.total_price()
    tax_rate = Decimal('0.10')
    tax      = round(subtotal * tax_rate, 2)
    total    = round(subtotal + tax, 2)
    return render(request, 'core/bill.html', {
        'order': order, 'items': items,
        'subtotal': subtotal, 'tax': tax,
        'total': total, 'tax_rate': int(tax_rate * 100),
    })


@role_required('waiter', 'admin')
def mark_paid(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'paid'
    order.save()
    order.table.is_occupied = False
    order.table.save()
    return redirect('dashboard')


# ── Kitchen Views ─────────────────────────────────────────

@role_required('chef', 'admin')
def kitchen(request):
    orders = Order.objects.filter(
        status__in=['pending', 'preparing']
    ).select_related('table').prefetch_related('items__menu_item').order_by('created_at')
    return render(request, 'core/kitchen.html', {'orders': orders})


@role_required('chef', 'admin')
def update_order_status(request, order_id):
    order      = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    if new_status in ['pending', 'preparing', 'served', 'paid']:
        order.status = new_status
        order.save()
        if new_status == 'paid':
            order.table.is_occupied = False
            order.table.save()
    return redirect('kitchen')
# ── Admin Dashboard ───────────────────────────────────────

@role_required('admin')
def admin_dashboard(request):
    total_orders   = Order.objects.count()
    paid_orders    = Order.objects.filter(status='paid')
    total_revenue  = sum(o.total_price() for o in paid_orders)
    total_users    = User.objects.count()
    total_tables   = Table.objects.count()
    total_items    = MenuItem.objects.count()
    recent_orders  = Order.objects.select_related('table').order_by('-created_at')[:10]

    context = {
        'total_orders':  total_orders,
        'total_revenue': total_revenue,
        'total_users':   total_users,
        'total_tables':  total_tables,
        'total_items':   total_items,
        'recent_orders': recent_orders,
        'paid_count':    paid_orders.count(),
    }
    return render(request, 'core/admin/dashboard.html', context)


# ── User Management ───────────────────────────────────────

@role_required('admin')
def admin_users(request):
    users = User.objects.select_related('profile').all().order_by('username')
    return render(request, 'core/admin/users.html', {'users': users})


@role_required('admin')
def admin_create_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        role     = request.POST['role']
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            user = User.objects.create_user(username=username, password=password)
            user.is_staff = True
            user.save()
            UserProfile.objects.get_or_create(user=user)
            user.profile.role = role
            user.profile.save()
            messages.success(request, f'✅ User "{username}" created as {role}.')
            return redirect('admin_users')
    return render(request, 'core/admin/create_user.html')


@role_required('admin')
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.username != request.user.username:
        user.delete()
        messages.success(request, '✅ User deleted.')
    else:
        messages.error(request, 'You cannot delete yourself.')
    return redirect('admin_users')


@role_required('admin')
def admin_edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        role = request.POST['role']
        user.profile.role = role
        user.profile.save()
        messages.success(request, f'✅ Role updated to {role}.')
        return redirect('admin_users')
    return render(request, 'core/admin/edit_user.html', {'u': user})


# ── Menu Management ───────────────────────────────────────

@role_required('admin')
def admin_menu(request):
    items = MenuItem.objects.all().order_by('category', 'name')
    return render(request, 'core/admin/menu.html', {'items': items})


@permission_required('can_add_menu')
def admin_create_menu_item(request):
    if request.method == 'POST':
        category  = request.POST['category']
        food_type = request.POST.get('food_type', 'na') if category == 'food' else 'na'
        MenuItem.objects.create(
            name         = request.POST['name'],
            price        = request.POST['price'],
            category     = category,
            food_type    = food_type,
            is_available = 'is_available' in request.POST,
        )
        messages.success(request, '✅ Menu item added.')
        return redirect('admin_menu')
    return render(request, 'core/admin/create_menu_item.html')


@permission_required('can_edit_menu')
def admin_edit_menu_item(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    if request.method == 'POST':
        category       = request.POST['category']
        item.name      = request.POST['name']
        item.price     = request.POST['price']
        item.category  = category
        item.food_type = request.POST.get('food_type', 'na') if category == 'food' else 'na'
        item.is_available = 'is_available' in request.POST
        item.save()
        messages.success(request, '✅ Menu item updated.')
        return redirect('admin_menu')
    return render(request, 'core/admin/edit_menu_item.html', {'item': item})

@permission_required('can_delete_menu')
def admin_delete_menu_item(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    item.delete()
    messages.success(request, '✅ Menu item deleted.')
    return redirect('admin_menu')


# ── Table Management ──────────────────────────────────────

@permission_required('can_add_table')
def admin_tables(request):
    tables = Table.objects.all().order_by('number')
    return render(request, 'core/admin/tables.html', {'tables': tables})


@permission_required('can_add_table')
def admin_create_table(request):
    if request.method == 'POST':
        number = request.POST['number']
        if Table.objects.filter(number=number).exists():
            messages.error(request, 'Table number already exists.')
        else:
            Table.objects.create(number=number)
            messages.success(request, f'✅ Table {number} added.')
        return redirect('admin_tables')
    return render(request, 'core/admin/create_table.html')


@permission_required('can_delete_table')
def admin_delete_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    table.delete()
    messages.success(request, '✅ Table deleted.')
    return redirect('admin_tables')


# ── Orders Overview ───────────────────────────────────────

@role_required('admin')
def admin_orders(request):
    status = request.GET.get('status', '')
    orders = Order.objects.select_related('table').prefetch_related(
        'items__menu_item'
    ).order_by('-created_at')
    if status:
        orders = orders.filter(status=status)

    statuses = [
        ('pending',   '⏳ Pending'),
        ('preparing', '🔥 Preparing'),
        ('served',    '✅ Served'),
        ('paid',      '💰 Paid'),
    ]
    return render(request, 'core/admin/orders.html', {
        'orders': orders, 'status': status, 'statuses': statuses
    })
from .models import RolePermission

@role_required('admin')
def admin_permissions(request):
    perms = RolePermission.get()
    if request.method == 'POST':
        perms.can_add_menu    = 'can_add_menu'    in request.POST
        perms.can_edit_menu   = 'can_edit_menu'   in request.POST
        perms.can_delete_menu = 'can_delete_menu' in request.POST
        perms.can_add_table   = 'can_add_table'   in request.POST
        perms.save()
        messages.success(request, '✅ Permissions updated.')
        return redirect('admin_permissions')
    return render(request, 'core/admin/permissions.html', {'perms': perms})
#=============================================================================
from django.http import JsonResponse
from django.utils import timezone as tz

def api_dashboard_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthorized'}, status=401)

    now    = tz.now()
    tables = Table.objects.all().order_by('number')
    active = []

    for table in tables:
        order = Order.objects.filter(
            table=table,
            status__in=['pending', 'preparing', 'served']
        ).prefetch_related('items__menu_item').first()
        if order:
            diff    = now - order.created_at
            minutes = int(diff.total_seconds() // 60)
            active.append({
                'table_number': table.number,
                'table_id':     table.id,
                'order_id':     order.id,
                'status':       order.status,
                'items_count':  order.items.count(),
                'total':        str(order.total_price()),
                'time':         order.created_at.strftime('%H:%M'),
                'minutes_ago':  minutes,
            })

    ready = Order.objects.filter(status='served').select_related('table')
    ready_list = [{'table': o.table.number, 'table_id': o.table.id, 'order_id': o.id} for o in ready]

    return JsonResponse({
        'active':        active,
        'ready_count':   ready.count(),
        'ready_orders':  ready_list,
        'pending_count': Order.objects.filter(status='pending').count(),
        'occupied':      Table.objects.filter(is_occupied=True).count(),
        'free':          Table.objects.filter(is_occupied=False).count(),
    })


def api_kitchen_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthorized'}, status=401)

    now    = tz.now()
    orders = Order.objects.filter(
        status__in=['pending', 'preparing']
    ).select_related('table').prefetch_related('items__menu_item').order_by('created_at')

    data = []
    for order in orders:
        diff    = now - order.created_at
        minutes = int(diff.total_seconds() // 60)
        data.append({
            'id':          order.id,
            'table':       order.table.number,
            'table_id':    order.table.id,
            'status':      order.status,
            'time':        order.created_at.astimezone().strftime('%H:%M'),
            'minutes_ago': minutes,
            'items': [
                {
                    'name':     i.menu_item.name,
                    'quantity': i.quantity,
                    'note':     i.note,
                }
                for i in order.items.all()
            ],
        })
    return JsonResponse({'orders': data})