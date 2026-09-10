from werkzeug.security import generate_password_hash, check_password_hash
from models import User


def register_user(db, fullname, phone, password):
    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        return None, "Bu telefon raqam allaqachon ro'yxatdan o'tgan"

    hashed = generate_password_hash(password)
    user = User(fullname=fullname, phone=phone, password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, None


def login_user(db, phone, password):
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        return None, "Foydalanuvchi topilmadi"
    if not check_password_hash(user.password, password):
        return None, "Parol noto'g'ri"
    return user, None
