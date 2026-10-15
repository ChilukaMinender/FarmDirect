from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation

from .models import Product
from .forms import ProductForm


def home(request):
    products = Product.objects.filter(
        is_available=True,
        quantity__gt=0,
    ).select_related("farmer").order_by("-created_at")[:8]

    categories = [
        ("vegetables", "🥦", "Vegetables"),
        ("fruits", "🍎", "Fruits"),
        ("grains", "🌾", "Grains"),
        ("dairy", "🥛", "Dairy"),
        ("other", "🧺", "Other"),
    ]

    return render(request, "home.html", {
        "products": products,
        "categories": categories,
    })


def farmer_required(view_func):
    """Allow only logged-in users whose profile role is farmer."""

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)

        if profile is None or profile.role != "farmer":
            messages.error(
                request,
                "Please log in with a farmer account to access this page."
            )
            return redirect("home")

        return view_func(request, *args, **kwargs)

    return wrapper


@farmer_required
def farmer_dashboard(request):
    products = Product.objects.filter(
        farmer=request.user
    ).order_by("-created_at")

    total_products = products.count()

    available_products = products.filter(
        is_available=True,
        quantity__gt=0,
    ).count()

    out_of_stock = products.filter(quantity=0).count()

    return render(request, "farmer/dashboard.html", {
        "products": products,
        "total_products": total_products,
        "available_products": available_products,
        "out_of_stock": out_of_stock,
    })


@farmer_required
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
            product.save()

            messages.success(
                request,
                "Your product has been added successfully!"
            )

            return redirect("farmer_dashboard")
    else:
        form = ProductForm()

    return render(request, "farmer/product_form.html", {
        "form": form,
        "page_title": "Add New Product",
        "button_text": "Add Product",
    })


@farmer_required
def edit_product(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        farmer=request.user,
    )

    if request.method == "POST":
        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your product has been updated successfully!"
            )

            return redirect("farmer_dashboard")
    else:
        form = ProductForm(instance=product)

    return render(request, "farmer/product_form.html", {
        "form": form,
        "page_title": "Edit Product",
        "button_text": "Save Changes",
        "product": product,
    })


@farmer_required
@require_POST
def delete_product(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        farmer=request.user,
    )

    product.delete()

    messages.success(
        request,
        "Your product has been deleted."
    )

    return redirect("farmer_dashboard")


def product_detail(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        is_available=True,
        quantity__gt=0,
    )

    return render(request, "products/product_detail.html", {
        "product": product,
    })

@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        is_available=True,
    )

    # Read the requested quantity.
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        return JsonResponse(
            {"success": False, "message": "Please enter a valid quantity."},
            status=400,
        )

    # Validate the quantity.
    if quantity < 1:
        return JsonResponse(
            {"success": False, "message": "Quantity must be at least 1."},
            status=400,
        )

    if quantity > product.quantity:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    f"Only {product.quantity} {product.unit} available."
                ),
            },
            status=400,
        )

    # Retrieve the customer's existing session cart.
    cart = request.session.get("cart", {})

    # Use the product ID as the cart key.
    product_id = str(product.pk)

    # Include quantities already in the cart when checking stock.
    existing_quantity = cart.get(product_id, 0)

    if existing_quantity + quantity > product.quantity:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    f"You can add only {product.quantity - existing_quantity} "
                    f"more {product.unit}."
                ),
            },
            status=400,
        )

    # Add the requested quantity.
    cart[product_id] = existing_quantity + quantity

    # Save the updated cart in the Django session.
    request.session["cart"] = cart
    request.session.modified = True

    return JsonResponse(
        {
            "success": True,
            "message": f"{product.name} added to your cart!",
            "cart_count": sum(cart.values()),
        }
    )
def cart_view(request):
    # Get the cart saved in the customer's session.
    cart = request.session.get("cart", {})

    cart_items = []
    total_amount = Decimal("0.00")
    updated_cart = {}

    # Get all products currently stored in the cart.
    products = Product.objects.filter(
        pk__in=cart.keys()
    ).select_related("farmer")

    products_by_id = {
        str(product.pk): product
        for product in products
    }

    for product_id, quantity in cart.items():

        product = products_by_id.get(str(product_id))

        # Ignore products that no longer exist.
        if product is None:
            continue

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            continue

        if quantity < 1:
            continue

        # Preserve the valid item in the session cart.
        updated_cart[str(product.pk)] = quantity

        # Calculate the subtotal for this product.
        subtotal = product.price * quantity
        total_amount += subtotal

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
            "available": (
                product.is_available
                and product.quantity >= quantity
                and product.quantity > 0
            ),
        })

    # Remove deleted or invalid products from the cart.
    if updated_cart != cart:
        request.session["cart"] = updated_cart

    return render(request, "cart/cart.html", {
        "cart_items": cart_items,
        "total_amount": total_amount,
    })

@require_POST
def update_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    cart = request.session.get("cart", {})
    product_id = str(product.pk)

    # Check whether the product exists in the cart.
    if product_id not in cart:
        messages.error(request, "This product is not in your cart.")
        return redirect("cart")

    # Read the new quantity.
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        messages.error(request, "Please enter a valid quantity.")
        return redirect("cart")

    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect("cart")

    # Check availability and stock.
    if not product.is_available or product.quantity < 1:
        messages.error(
            request,
            f"{product.name} is currently unavailable."
        )
        return redirect("cart")

    if quantity > product.quantity:
        messages.error(
            request,
            f"Only {product.quantity} {product.unit} available."
        )
        return redirect("cart")

    # Update the cart quantity.
    cart[product_id] = quantity
    request.session["cart"] = cart
    request.session.modified = True

    messages.success(
        request,
        f"{product.name} quantity updated successfully."
    )

    return redirect("cart")


@require_POST
def remove_from_cart(request, pk):
    cart = request.session.get("cart", {})
    product_id = str(pk)

    if product_id in cart:
        del cart[product_id]

        request.session["cart"] = cart
        request.session.modified = True

        messages.success(request, "Product removed from your cart.")
    else:
        messages.error(request, "This product is not in your cart.")

    return redirect("cart")