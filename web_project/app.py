from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Инициализация Flask
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Конфигурация базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------- Модели базы данных ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'manager' или 'user'
    is_active = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    delivery_time = db.Column(db.Integer, nullable=False)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)  # Убедитесь, что 'product.id' существует
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Дата продажи
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Ссылка на 'user.id'



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'pending', 'approved', 'rejected'

# ---------- Главная страница ----------
@app.route('/')
def home():
    logged_in = 'user_id' in session
    role = session.get('role') if logged_in else None
    return render_template('home.html', logged_in=logged_in, role=role)

# ---------- Регистрация ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        role = 'user'

        if User.query.filter_by(email=email).first():
            flash("Email уже зарегистрирован.")
            return render_template('register.html')

        new_user = User(username=username, email=email, password=password, role=role, is_active=False)
        db.session.add(new_user)
        db.session.commit()
        flash("Регистрация прошла успешно! Ожидайте подтверждения менеджера.")
        return redirect(url_for('login', role=role))

    return render_template('register.html')

# ---------- Вход ----------
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, role=role).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            if role == 'manager':
                return redirect(url_for('manager_dashboard'))
            elif role == 'user':
                return redirect(url_for('user_dashboard'))
        flash("Неверные учетные данные.")
    return render_template('login.html', role=role)

# ---------- Выход ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Вы вышли из системы.")
    return redirect(url_for('home'))

# ---------- Панель менеджера ----------
@app.route('/manager_dashboard')
def manager_dashboard():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('login', role='manager'))

    users = User.query.filter_by(role='user').all()
    sales = Sale.query.all()
    for sale in sales:
        print(sale.sale_date)
    inventory = Product.query.all()
    return render_template('manager_dashboard.html', users=users, sales=sales, inventory=inventory)

# ---------- Панель пользователя ----------
@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('login', role='user'))

    user = User.query.get(session['user_id'])
    sales = Sale.query.filter_by(user_id=user.id).all()
    products = Product.query.filter_by(user_id=user.id).all()
    return render_template('user_dashboard.html', sales=sales, products=products)

# ---------- Добавление продаж ----------
@app.route('/add_sale', methods=['POST'])
def add_sale():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('login', role='user'))

    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])

    product = Product.query.get(product_id)
    if not product or product.stock < quantity:
        flash("Недостаточно товара на складе.")
        return redirect(url_for('user_dashboard'))

    total_price = product.price * quantity
    product.stock -= quantity

    new_sale = Sale(
        product_id=product_id,
        quantity=quantity,
        total_price=total_price,
        user_id=session['user_id']
    )
    db.session.add(new_sale)
    db.session.commit()
    flash("Продажа успешно добавлена.")
    return redirect(url_for('user_dashboard'))

# ---------- Управление пользователями ----------
@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('login', role='manager'))

    inactive_users = User.query.filter_by(is_active=False).all()
    active_users = User.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        user = User.query.get(user_id)

        if action == 'approve':
            user.is_active = True
        elif action == 'delete':
            db.session.delete(user)

        db.session.commit()
        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', inactive_users=inactive_users, active_users=active_users)

# ---------- Управление инвентарем ----------
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user_id' not in session:
        return redirect(url_for('login', role='manager'))

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        user_id = session['user_id']

        new_product = Product(name=name, price=price, stock=stock, user_id=user_id)
        db.session.add(new_product)
        db.session.commit()
        flash("Продукт успешно добавлен в инвентарь.")
        return redirect(url_for('inventory'))

    products = Product.query.filter_by(user_id=session['user_id']).all()
    return render_template('inventory.html', products=products)

# ---------- Управление поставщиками ----------
@app.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('login', role='manager'))

    products = Product.query.all()
    suppliers = Supplier.query.all()

    if request.method == 'POST':
        product_id = request.form['product_id']
        name = request.form['name']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        delivery_time = int(request.form['delivery_time'])

        new_supplier = Supplier(
            product_id=product_id,
            name=name,
            quantity=quantity,
            price=price,
            delivery_time=delivery_time
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash("Поставщик успешно добавлен.")
        return redirect(url_for('suppliers'))

    return render_template('suppliers.html', products=products, suppliers=suppliers)

# ---------- Подтверждение заказов ----------
@app.route('/confirm_orders', methods=['GET', 'POST'])
def confirm_orders():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('login', role='manager'))

    orders = Order.query.filter_by(status='pending').all()

    if request.method == 'POST':
        order_id = request.form['order_id']
        action = request.form['action']
        order = Order.query.get(order_id)

        if action == 'approve':
            order.status = 'approved'
        elif action == 'reject':
            order.status = 'rejected'

        db.session.commit()
        return redirect(url_for('confirm_orders'))

    return render_template('confirm_orders.html', orders=orders)

# ---------- Аналитика ----------
@app.route('/analytics', methods=['GET'])
def analytics():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('login', role='manager'))

    total_sales = db.session.query(db.func.sum(Sale.total_price)).scalar() or 0
    total_products_sold = db.session.query(db.func.sum(Sale.quantity)).scalar() or 0
    low_stock_products = Product.query.filter(Product.stock < 10).all()
    sales_history = Sale.query.all()

    return render_template(
        'analytics.html',
        total_sales=total_sales,
        total_products_sold=total_products_sold,
        low_stock_products=low_stock_products,
        sales_history=sales_history
    )

# ---------- Запуск приложения ----------
if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
    app.run(debug=True)
