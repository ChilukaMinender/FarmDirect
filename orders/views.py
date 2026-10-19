from decimal import Decimal

from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from products.models import Product
from .models import Order, OrderItem, Notification


def customer_display_number(order):
    """Return this customer's sequential order number, starting at 1."""
    return Order.objects.filter(
        customer=order.customer,
    ).filter(
        Q(created_at__lt=order.created_at)
        | Q(created_at=order.created_at, pk__lte=order.pk)
    ).count()


def farmer_display_number(order, farmer):
    """Return the sequential number for this farmer's orders."""
    return Order.objects.filter(
        items__product__farmer=farmer,
    ).filter(
        Q(created_at__lt=order.created_at)
        | Q(created_at=order.created_at, pk__lte=order.pk)
    ).distinct().count()


@login_required
def checkout(request):
    cart = request.session.get("cart", {})

    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect("cart")

    try:
        cart_items_requested = {
            int(product_id): int(quantity)
            for product_id, quantity in cart.items()
        }
    except (TypeError, ValueError):
        request.session["cart"] = {}
        request.session.modified = True
        messages.error(
            request,
            "Your cart contains invalid items. Please add products again.",
        )
        return redirect("cart")

    if any(
        product_id <= 0 or quantity <= 0
        for product_id, quantity in cart_items_requested.items()
    ):
        messages.error(request, "Your cart contains invalid quantities.")
        return redirect("cart")

    product_ids = list(cart_items_requested.keys())

    products = Product.objects.filter(
        id__in=product_ids,
        is_available=True,
    )

    product_map = {product.pk: product for product in products}

    cart_items = []
    total = Decimal("0.00")

    for product_id, quantity in cart_items_requested.items():
        product = product_map.get(product_id)

        if product is None or product.quantity < 1:
            messages.error(
                request,
                "A product in your cart is unavailable. Please review your cart.",
            )
            return redirect("cart")

        if quantity > product.quantity:
            messages.error(
                request,
                f"Only {product.quantity} {product.unit} of "
                f"{product.name} are available.",
            )
            return redirect("cart")

        subtotal = product.price * quantity
        total += subtotal

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    if request.method == "POST":
        address = request.POST.get("delivery_address", "").strip()

        if len(address) < 10:
            messages.error(
                request,
                "Please enter a complete delivery address.",
            )
            return render(
                request,
                "orders/checkout.html",
                {"cart_items": cart_items, "total": total},
            )

        with transaction.atomic():
            locked_products = {
                product.pk: product
                for product in Product.objects.select_for_update().filter(
                    id__in=product_ids
                )
            }

            validated_items = []
            locked_total = Decimal("0.00")

            for product_id, quantity in cart_items_requested.items():
                product = locked_products.get(product_id)

                if (
                    product is None
                    or not product.is_available
                    or product.quantity < quantity
                ):
                    messages.error(
                        request,
                        "Stock changed while you were checking out. "
                        "Please review your cart.",
                    )
                    return redirect("cart")

                locked_total += product.price * quantity

                validated_items.append({
                    "product": product,
                    "quantity": quantity,
                })

            order = Order.objects.create(
                customer=request.user,
                delivery_address=address,
                total_amount=locked_total,
                status="pending",
            )

            # Create order items and update product stock.
            for item in validated_items:
                product = item["product"]
                quantity = item["quantity"]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price,
                )

                product.quantity -= quantity

                if product.quantity == 0:
                    product.is_available = False

                product.save(
                    update_fields=["quantity", "is_available"]
                )

            # Notify every farmer whose products are in this order.
            # Each farmer receives only one notification per order.
            notified_farmers = set()

            for item in validated_items:
                farmer = item["product"].farmer

                if farmer.pk in notified_farmers:
                    continue

                farmer_order_number = farmer_display_number(
                    order,
                    farmer,
                )

                Notification.objects.create(
                    recipient=farmer,
                    order=order,
                    message=(
                        f"New order received! "
                        f"Order #{farmer_order_number} has been placed."
                    ),
                )

                notified_farmers.add(farmer.pk)

        request.session["cart"] = {}
        request.session.modified = True

        display_number = customer_display_number(order)

        messages.success(
            request,
            f"Order #{display_number} placed successfully!",
        )

        return redirect("order_detail", pk=order.pk)

    return render(
        request,
        "orders/checkout.html",
        {"cart_items": cart_items, "total": total},
    )


@login_required
def my_orders(request):
    orders = list(
        Order.objects.filter(
            customer=request.user
        ).order_by("-created_at", "-id")
    )

    total_orders = len(orders)

    for index, order in enumerate(orders):
        order.display_number = total_orders - index

    return render(request, "orders/my_orders.html", {
        "orders": orders,
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        pk=pk,
        customer=request.user,
    )

    display_number = customer_display_number(order)

    return render(request, "orders/order_detail.html", {
        "order": order,
        "display_number": display_number,
    })


@login_required
def farmer_orders(request):
    if (
        not hasattr(request.user, "profile")
        or request.user.profile.role != "farmer"
    ):
        messages.error(request, "Only farmers can access farmer orders.")
        return redirect("home")

    orders = list(
        Order.objects.filter(
            items__product__farmer=request.user
        )
        .distinct()
        .order_by("-created_at", "-id")
        .prefetch_related("items__product")
    )

    farmer_order_data = []
    total_orders = len(orders)

    for index, order in enumerate(orders):
        farmer_items = [
            {
                "item": item,
                "subtotal": item.price * item.quantity,
            }
            for item in order.items.all()
            if item.product.farmer_id == request.user.id
        ]

        display_number = total_orders - index

        order.display_number = display_number

        farmer_order_data.append({
            "order": order,
            "display_number": display_number,
            "items": farmer_items,
            "farmer_subtotal": sum(
                (entry["subtotal"] for entry in farmer_items),
                Decimal("0.00"),
            ),
        })

    return render(request, "orders/farmer_orders.html", {
        "orders": orders,
        "farmer_order_data": farmer_order_data,
    })


@login_required
def farmer_order_detail(request, pk):
    try:
        if (
            not hasattr(request.user, "profile")
            or request.user.profile.role != "farmer"
        ):
            messages.error(
                request,
                "Only farmers can access farmer order details.",
            )
            return redirect("home")

        order = get_object_or_404(
            Order.objects.filter(
                items__product__farmer=request.user,
            ).distinct().prefetch_related("items__product"),
            pk=pk,
        )

        items = [
            {
                "product": item.product,
                "quantity": item.quantity,
                "price": item.price,
                "subtotal": item.price * item.quantity,
            }
            for item in order.items.all()
            if item.product.farmer_id == request.user.id
        ]

        farmer_subtotal = sum(
            (item["subtotal"] for item in items),
            Decimal("0.00"),
        )

        display_number = farmer_display_number(order, request.user)

        return render(
            request,
            "orders/farmer_order_detail.html",
            {
                "order": order,
                "items": items,
                "farmer_subtotal": farmer_subtotal,
                "display_number": display_number,
            },
        )

    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "FARMER ORDER DETAIL ERROR: order_id=%s, user_id=%s",
            pk,
            request.user.pk,
        )
        raise


@login_required
@require_POST
def update_order_status(request, pk):
    if (
        not hasattr(request.user, "profile")
        or request.user.profile.role != "farmer"
    ):
        messages.error(
            request,
            "Only farmers can update order statuses.",
        )
        return redirect("home")

    order = get_object_or_404(
        Order.objects.filter(
            items__product__farmer=request.user
        ).distinct(),
        pk=pk,
    )

    new_status = request.POST.get("status", "").strip()

    allowed_statuses = {"confirmed", "shipped", "delivered"}

    if new_status not in allowed_statuses:
        messages.error(
            request,
            "Invalid status. Farmers can confirm, ship, or deliver orders.",
        )
        return redirect("farmer_orders")

    if order.status in {"delivered", "cancelled"}:
        messages.error(
            request,
            "Delivered or cancelled orders cannot be changed.",
        )
        return redirect("farmer_orders")

    valid_transitions = {
        "pending": {"confirmed"},
        "confirmed": {"shipped"},
        "shipped": {"delivered"},
    }

    if new_status not in valid_transitions.get(order.status, set()):
        messages.error(
            request,
            f"Cannot change order status from {order.status} to {new_status}.",
        )
        return redirect("farmer_orders")

    order.status = new_status
    order.save(update_fields=["status"])

    display_number = farmer_display_number(
        order,
        request.user,
    )

    customer_number = customer_display_number(order)

    Notification.objects.create(
        recipient=order.customer,
        order=order,
        message=(
            f"Your order #{customer_number} is now "
            f"{order.get_status_display().lower()}."
        ),
    )

    messages.success(
        request,
        f"Order #{display_number} status updated successfully.",
    )

    return redirect("farmer_orders")


@login_required
@require_POST
def cancel_order(request, pk):
    """Cancel a customer's pending order and restore product stock."""

    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update(),
            pk=pk,
            customer=request.user,
        )

        if order.status != "pending":
            messages.error(
                request,
                "Only pending orders can be cancelled.",
            )
            return redirect("order_detail", pk=order.pk)

        items = list(order.items.all())
        product_ids = [item.product_id for item in items]

        locked_products = {
            product.pk: product
            for product in Product.objects.select_for_update().filter(
                pk__in=product_ids
            )
        }

        if any(
            item.product_id not in locked_products
            for item in items
        ):
            messages.error(
                request,
                "A product could not be found. Please contact support.",
            )
            return redirect("order_detail", pk=order.pk)

        for item in items:
            product = locked_products[item.product_id]
            product.quantity += item.quantity
            product.is_available = product.quantity > 0
            product.save(
                update_fields=["quantity", "is_available"]
            )

        order.status = "cancelled"
        order.save(update_fields=["status"])

    display_number = customer_display_number(order)

    messages.success(
        request,
        f"Order #{display_number} was cancelled successfully. "
        "Product stock has been restored.",
    )

    return redirect("order_detail", pk=order.pk)


@login_required
def customer_notifications(request):
    notifications = Notification.objects.filter(
        recipient=request.user,
    ).select_related("order")

    return render(
        request,
        "orders/notifications.html",
        {"notifications": notifications},
    )


@login_required
@require_POST
def mark_notification_read(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )

    notification.is_read = True
    notification.save(update_fields=["is_read"])

    return redirect("customer_notifications")


@login_required
def notification_status(request):
    notifications = Notification.objects.filter(
        recipient=request.user,
    )

    latest = notifications.first()

    return JsonResponse({
        "unread_count": notifications.filter(is_read=False).count(),
        "latest_id": latest.pk if latest else None,
        "latest_message": latest.message if latest else "",
    })

