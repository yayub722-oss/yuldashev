from flask  import Flask, render_template, request, redirect, url_for, session, flash
from database import init_db, SessionLocal
from services.auth_service import register_user, login_user
from services.product_service import (
    get_all_products, get_product, get_all_categories,
    create_product, update_product, delete_product
)
from services.order_service import (
    create_order, get_user_orders, get_all_orders,
    update_order_status, get_order_detail
)

app = Flask(__name__)
app.secret_key = "supersecretkey_change_in_production"
app.config["UPLOAD_FOLDER"] = "uploads"

init_db()


def get_db():
    return SessionLocal()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Iltimos avval tizimga kiring", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Ruxsat yo'q", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated


# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db = get_db()
        user, error = register_user(
            db,
            fullname=request.form["fullname"],
            phone=request.form["phone"],
            password=request.form["password"],
        )
        db.close()
        if error:
            flash(error, "danger")
            return redirect(url_for("register"))
        flash("Muvaffaqiyatli ro'yxatdan o'tdingiz!", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        user, error = login_user(db, request.form["phone"], request.form["password"])
        db.close()
        if error:
            flash(error, "danger")
            return redirect(url_for("login"))
        session["user_id"] = user.id
        session["fullname"] = user.fullname
        session["is_admin"] = user.is_admin
        flash(f"Xush kelibsiz, {user.fullname}!", "success")
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ─── SHOP ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    db = get_db()
    products = get_all_products(db, search=request.args.get("q"), category_id=request.args.get("category_id"))
    categories = get_all_categories(db)
    result = render_template("home.html", products=products, categories=categories)
    db.close()
    return result


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    product = get_product(db, product_id)
    if not product:
        db.close()
        flash("Mahsulot topilmadi", "warning")
        return redirect(url_for("home"))
    result = render_template("product_detail.html", product=product)
    db.close()
    return result


# ─── CART ────────────────────────────────────────────────────────────────────

@app.route("/cart")
@login_required
def cart():
    cart_items = session.get("cart", [])
    db = get_db()
    items = []
    total = 0
    for item in cart_items:
        product = get_product(db, item["product_id"])
        if product:
            subtotal = product.price * item["quantity"]
            total += subtotal
            items.append({"product": product, "quantity": item["quantity"], "subtotal": subtotal})
    result = render_template("cart.html", items=items, total=total)
    db.close()
    return result


@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    cart_items = session.get("cart", [])
    quantity = int(request.form.get("quantity", 1))
    for item in cart_items:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            break
    else:
        cart_items.append({"product_id": product_id, "quantity": quantity})
    session["cart"] = cart_items
    flash("Savatga qo'shildi!", "success")
    return redirect(request.referrer or url_for("home"))


@app.route("/cart/remove/<int:product_id>")
@login_required
def remove_from_cart(product_id):
    cart_items = session.get("cart", [])
    session["cart"] = [i for i in cart_items if i["product_id"] != product_id]
    return redirect(url_for("cart"))


# ─── CHECKOUT ────────────────────────────────────────────────────────────────

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if request.method == "POST":
        cart_items = session.get("cart", [])
        if not cart_items:
            flash("Savat bo'sh!", "warning")
            return redirect(url_for("cart"))

        city     = request.form.get("city", "")
        district = request.form.get("district", "")
        street   = request.form.get("street", "")
        house    = request.form.get("house", "")
        note     = request.form.get("note", "")
        payment  = request.form.get("payment", "cash")
        lat      = request.form.get("lat", "")
        lng      = request.form.get("lng", "")

        full_address = f"{city}, {district}, {street}, {house}"
        if note:
            full_address += f" ({note})"
        if lat and lng:
            full_address += f" [📍{lat},{lng}]"

        db = get_db()
        order, error = create_order(
            db,
            user_id=session["user_id"],
            cart=cart_items,
            address=full_address,
        )
        db.close()

        if error:
            flash(error, "danger")
            return redirect(url_for("cart"))

        session["cart"] = []
        pay_text = {"cash": "Naqt pul", "payme": "Payme", "click": "Click", "card": "Karta"}.get(payment, payment)
        flash(f"✅ Buyurtma #{order.id} qabul qilindi! To'lov: {pay_text}", "success")
        return redirect(url_for("my_orders"))

    return render_template("checkout.html")


# ─── ORDERS ──────────────────────────────────────────────────────────────────

@app.route("/orders")
@login_required
def my_orders():
    db = get_db()
    orders = get_user_orders(db, session["user_id"])
    result = render_template("orders.html", orders=orders)
    db.close()
    return result


# ─── ADMIN ───────────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required
@admin_required
def admin_panel():
    db = get_db()
    products = get_all_products(db)
    orders = get_all_orders(db)
    result = render_template("admin.html", products=products, orders=orders)
    db.close()
    return result


@app.route("/admin/product/add", methods=["POST"])
@login_required
@admin_required
def admin_add_product():
    db = get_db()
    create_product(
        db,
        name=request.form["name"],
        description=request.form.get("description", ""),
        price=request.form["price"],
        stock=request.form["stock"],
        category_id=request.form.get("category_id"),
        image_file=request.files.get("image"),
    )
    db.close()
    flash("Mahsulot qo'shildi!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/product/delete/<int:product_id>")
@login_required
@admin_required
def admin_delete_product(product_id):
    db = get_db()
    delete_product(db, product_id)
    db.close()
    flash("Mahsulot o'chirildi", "info")
    return redirect(url_for("admin_panel"))


@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
@login_required
@admin_required
def admin_update_order(order_id):
    db = get_db()
    update_order_status(db, order_id, request.form["status"])
    db.close()
    flash("Buyurtma holati yangilandi", "success")
    return redirect(url_for("admin_panel"))


if __name__ == "__main__":
    app.run(debug=True)


# ─── CATALOG ─────────────────────────────────────────────────────────────────

@app.route("/catalog")
def catalog():
    db = get_db()
    from models import Product
    from sqlalchemy.orm import joinedload

    category_id = request.args.get("category_id")
    search      = request.args.get("q")
    min_price   = request.args.get("min_price")
    max_price   = request.args.get("max_price")
    in_stock    = request.args.get("in_stock")
    sort        = request.args.get("sort")

    query = db.query(Product).options(joinedload(Product.category))

    if category_id:
        query = query.filter(Product.category_id == int(category_id))
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if min_price:
        query = query.filter(Product.price >= float(min_price))
    if max_price:
        query = query.filter(Product.price <= float(max_price))
    if in_stock:
        query = query.filter(Product.stock > 0)
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "new":
        query = query.order_by(Product.created_at.desc())

    products   = query.all()
    categories = get_all_categories(db)
    result = render_template("catalog.html", products=products, categories=categories)
    db.close()
    return result


# ─── WISHLIST ────────────────────────────────────────────────────────────────

@app.route("/wishlist")
@login_required
def wishlist():
    wish = session.get("wishlist", [])
    db = get_db()
    from services.product_service import get_product
    products = [get_product(db, pid) for pid in wish]
    products = [p for p in products if p]
    result = render_template("wishlist.html", products=products)
    db.close()
    return result


@app.route("/wishlist/toggle/<int:product_id>")
@login_required
def wishlist_toggle(product_id):
    wish = session.get("wishlist", [])
    if product_id in wish:
        wish.remove(product_id)
        flash("Sevimlilardan o'chirildi", "info")
    else:
        wish.append(product_id)
        flash("Sevimlilarga qo'shildi ❤️", "success")
    session["wishlist"] = wish
    return redirect(request.referrer or url_for("home"))
