import os
from models import Product, Category
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "uploads/products"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_all_products(db, category_id=None, search=None):
    query = db.query(Product).options(joinedload(Product.category))
    if category_id:
        query = query.filter(Product.category_id == int(category_id))
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    return query.all()


def get_product(db, product_id):
    return db.query(Product).options(joinedload(Product.category)).filter(Product.id == product_id).first()


def get_all_categories(db):
    return db.query(Category).all()


def create_product(db, name, description, price, stock, category_id, image_file=None):
    image_path = None
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(save_path)
        image_path = save_path

    product = Product(
        name=name,
        description=description,
        price=float(price),
        stock=int(stock),
        category_id=int(category_id) if category_id else None,
        image=image_path,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db, product_id, **kwargs):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    for key, value in kwargs.items():
        if hasattr(product, key) and value is not None:
            setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db, product_id):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        db.delete(product)
        db.commit()
        return True
    return False
