from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'supersecretkey'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

USER_LIMIT = 10

# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # manager, user
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # ID менеджера для пользователя
    is_active = db.Column(db.Boolean, default=False)  # Активен ли пользователь

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=5)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_standard = db.Column(db.Boolean, default=False)  # Является ли продукт стандартным

class ShoppingCart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Предзагрузка стандартных продуктов
def load_standard_products():
    standard_products = ["Coffee", "Croissant", "Juice"]
    for product_name in standard_products:
        existing_product = Inventory.query.filter_by(product_name=product_name, is_standard=True).first()
        if not existing_product:
            product = Inventory(product_name=product_name, quantity=0, min_stock=5, is_standard=True)
            db.session.add(product)
    db.session.commit()

# Функция отправки email
def send_email_to_supplier(subject, body, recipient):
    sender_email = "your_email@example.com"
    sender_password = "your_password"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

# Корзина: добавление товара
@app.route('/shopping_cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'role' not in session or session['role'] != 'manager':
        return "Access denied."

    quantity = int(request.form['quantity'])
    manager_id = session['user_id']

    new_item = ShoppingCart(product_id=product_id, quantity=quantity, manager_id=manager_id)
    db.session.add(new_item)
    db.session.commit()
    return redirect(url_for('view_cart'))

# Корзина: просмотр
@app.route('/shopping_cart')
def view_cart():
    if 'role' not in session or session['role'] != 'manager':
        return "Access denied."

    manager_id = session['user_id']
    cart_items = db.session.query(ShoppingCart, Inventory).join(Inventory).filter(ShoppingCart.manager_id == manager_id).all()
    return render_template('shopping_cart.html', cart_items=cart_items)

# Корзина: оформление заказа
@app.route('/shopping_cart/checkout', methods=['POST'])
def checkout():
    if 'role' not in session or session['role'] != 'manager':
        return "Access denied."

    manager_id = session['user_id']
    cart_items = db.session.query(ShoppingCart, Inventory).join(Inventory).filter(ShoppingCart.manager_id == manager_id).all()

    order_details = []
    for cart_item, product in cart_items:
        order_details.append(f"{product.product_name}: {cart_item.quantity}")
        product.quantity += cart_item.quantity
        db.session.delete(cart_item)

    db.session.commit()

    # Отправляем email поставщику
    order_text = "\n".join(order_details)
    send_email_to_supplier(
        subject="New Order from ERP System",
        body=f"Order Details:\n{order_text}",
        recipient="supplier@example.com"
    )
    return redirect(url_for('view_cart'))

# Создание базы данных
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        load_standard_products()
    app.run(debug=True)
