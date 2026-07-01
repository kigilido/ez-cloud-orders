import calendar
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.billing.models import Invoice, MonthEndStatement
from apps.billing.services import billing_service
from apps.customers.models import Customer
from apps.customers.services import check_eligibility
from apps.orders.models import InboundOrder, Order
from apps.orders.services import (
    create_order,
    get_duplicate_orders,
    get_pending_inbound_orders,
    has_duplicate_warning,
)

USER_ROLES = {
    "operator": {"label": "Operator", "is_staff": False, "is_superuser": False},
    "staff": {"label": "Staff", "is_staff": True, "is_superuser": False},
    "superuser": {"label": "Superuser", "is_staff": True, "is_superuser": True},
}


def _user_role(user: User) -> str:
    if user.is_superuser:
        return "superuser"
    if user.is_staff:
        return "staff"
    return "operator"


def _apply_user_role(user: User, role: str) -> None:
    role_config = USER_ROLES.get(role, USER_ROLES["operator"])
    user.is_staff = role_config["is_staff"]
    user.is_superuser = role_config["is_superuser"]


def _can_assign_roles(user: User) -> bool:
    return user.is_superuser


@login_required
def home(request: HttpRequest) -> HttpResponse:
    today = date.today()
    first_of_month = today.replace(day=1)

    # Last month window
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)

    hour = today.timetuple().tm_hour  # not reliable for greeting but we have datetime below
    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    total_customers = Customer.objects.count()
    eligible_customers = Customer.objects.filter(valid_until__gte=today).count()
    orders_this_month = Order.objects.filter(created_at__date__gte=first_of_month).count()
    orders_last_month = Order.objects.filter(
        created_at__date__gte=last_month_start,
        created_at__date__lt=first_of_month,
    ).count()
    pending_inbound = InboundOrder.objects.filter(outbound_orders__isnull=True).count()
    recent_orders = Order.objects.select_related("customer").order_by("-created_at")[:10]

    return render(
        request,
        "dashboard/home.html",
        {
            "greeting": greeting,
            "total_customers": total_customers,
            "eligible_customers": eligible_customers,
            "orders_this_month": orders_this_month,
            "orders_last_month": orders_last_month,
            "pending_inbound": pending_inbound,
            "recent_orders": recent_orders,
            "today": today,
        },
    )


@login_required
def search(request: HttpRequest) -> HttpResponse:
    phone = request.GET.get("phone", "").strip()
    result = None
    pending_inbound_orders = InboundOrder.objects.none()
    if phone:
        result = check_eligibility(phone)
        if result["found"]:
            pending_inbound_orders = get_pending_inbound_orders(result["customer"])
    return render(
        request,
        "dashboard/search.html",
        {
            "phone": phone,
            "result": result,
            "pending_inbound_orders": pending_inbound_orders,
        },
    )


@login_required
def order_confirm(
    request: HttpRequest,
    customer_id: int,
    inbound_order_id: int,
) -> HttpResponse:
    customer = get_object_or_404(Customer, pk=customer_id)
    inbound_order = get_object_or_404(
        get_pending_inbound_orders(customer),
        pk=inbound_order_id,
    )
    duplicate_warning = has_duplicate_warning(customer)
    existing_orders = get_duplicate_orders(customer) if duplicate_warning else []

    if request.method == "POST":
        force = request.POST.get("confirm_duplicate") == "yes" or not duplicate_warning
        order, error = create_order(
            customer=customer,
            inbound_order=inbound_order,
            created_by=request.user,
            force=force,
        )
        if order:
            return render(
                request,
                "dashboard/order_confirm.html",
                {"order": order, "customer": customer},
            )
        return render(
            request,
            "dashboard/order_confirm.html",
            {
                "error": error,
                "customer": customer,
                "inbound_order": inbound_order,
                "duplicate_warning": True,
                "existing_orders": existing_orders,
            },
        )

    return render(
        request,
        "dashboard/order_confirm.html",
        {
            "customer": customer,
            "inbound_order": inbound_order,
            "duplicate_warning": duplicate_warning,
            "existing_orders": existing_orders,
        },
    )


@login_required
def month_end(request: HttpRequest) -> HttpResponse:
    period_start, period_end = billing_service.resolve_period()
    recent_statements = MonthEndStatement.objects.all()[:5]
    current_complete = MonthEndStatement.objects.filter(
        period_start=period_start,
        period_end=period_end,
        status="complete",
    ).first()

    if request.method == "POST":
        statement = billing_service.run(
            period_start=period_start,
            period_end=period_end,
            force=True,
        )
        if statement.status == "complete":
            pdf_name = (
                statement.pdf_file.name.split("/")[-1]
                if statement.pdf_file
                else "Statement generated."
            )
            messages.success(
                request,
                f"Month-end complete for {period_start:%b %d} — {period_end:%b %d, %Y}. {pdf_name}",
            )
        else:
            messages.error(
                request,
                f"Month-end failed: {statement.error_log or 'Unknown error'}",
            )
        return redirect("dashboard:month_end")

    return render(
        request,
        "dashboard/month_end.html",
        {
            "period_start": period_start,
            "period_end": period_end,
            "recent_statements": recent_statements,
            "current_complete": current_complete,
        },
    )


@login_required
def statement_detail(request: HttpRequest, statement_id: int) -> HttpResponse:
    statement = get_object_or_404(MonthEndStatement, pk=statement_id)
    from apps.billing.services import billing_service as bs
    orders = bs.get_orders_for_period(statement.period_start, statement.period_end)
    invoices = Invoice.objects.filter(order__in=orders).select_related("order", "order__customer")
    return render(
        request,
        "dashboard/statement_detail.html",
        {
            "statement": statement,
            "orders": orders,
            "invoices": invoices,
        },
    )


@login_required
def user_list(request: HttpRequest) -> HttpResponse:
    users = User.objects.all().order_by("username")
    return render(request, "dashboard/user_list.html", {"users": users})


@login_required
def user_add(request: HttpRequest) -> HttpResponse:
    can_assign_roles = _can_assign_roles(request.user)
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        role = request.POST.get("role", "operator")
        if not can_assign_roles:
            role = "operator"
        if role not in USER_ROLES:
            role = "operator"
        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect("dashboard:user_add")
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect("dashboard:user_add")
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        _apply_user_role(user, role)
        user.save()
        messages.success(
            request,
            f"User '{username}' created as {USER_ROLES[role]['label']}.",
        )
        return redirect("dashboard:user_list")
    return render(
        request,
        "dashboard/user_form.html",
        {
            "action": "Add",
            "can_assign_roles": can_assign_roles,
            "roles": USER_ROLES,
            "selected_role": "operator",
        },
    )


@login_required
def user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    user = get_object_or_404(User, pk=user_id)
    can_assign_roles = _can_assign_roles(request.user)
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        new_password = request.POST.get("password", "").strip()
        user.email = email
        if new_password:
            user.set_password(new_password)
        if can_assign_roles and user != request.user:
            role = request.POST.get("role", _user_role(user))
            if role not in USER_ROLES:
                role = _user_role(user)
            _apply_user_role(user, role)
        user.save()
        messages.success(request, f"User '{user.username}' updated.")
        return redirect("dashboard:user_list")
    return render(
        request,
        "dashboard/user_form.html",
        {
            "action": "Edit",
            "edit_user": user,
            "can_assign_roles": can_assign_roles,
            "roles": USER_ROLES,
            "selected_role": _user_role(user),
        },
    )


@login_required
def user_toggle(request: HttpRequest, user_id: int) -> HttpResponse:
    user = get_object_or_404(User, pk=user_id)
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("dashboard:user_list")
    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User '{user.username}' {status}.")
    return redirect("dashboard:user_list")
