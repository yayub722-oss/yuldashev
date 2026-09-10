from models import Order, OrderItem, Product


def create_order(db, user_id, cart, address):
    """
    cart = [{"product_id": 1, "quantity": 2}, ...]
    """
    total = 0
    items_data = []

    for item in cart:
        product = db.query(Product).filter(Product.id == item["product_id"]).first()
        if not product:
            return None, f"Mahsulot topilmadi: {item['product_id']}"
        if product.stock < item["quantity"]:
            return None, f"'{product.name}' omborda yetarli emas"

        subtotal = product.price * item["quantity"]
        total += subtotal
        items_data.append((product, item["quantity"], product.price))

    order = Order(user_id=user_id, total_price=total, address=address)
    db.add(order)
    db.flush()

    for product, quantity, price in items_data:
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            price=price,
        )
        product.stock -= quantity
        db.add(order_item)

    db.commit()
    db.refresh(order)
    return order, None


def get_user_orders(db, user_id):
    return db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()


def get_all_orders(db):
    return db.query(Order).order_by(Order.created_at.desc()).all()


def update_order_status(db, order_id, status):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None
    order.status = status
    db.commit()
    return order


def get_order_detail(db, order_id):
    return db.query(Order).filter(Order.id == order_id).first()
