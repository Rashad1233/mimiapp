from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from web_project.forms import RegistrationForm, LoginForm, AddProductForm, AddSupplierForm, FilterSalesForm
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
from your_database_module import db, User  # Adjust your import paths




app = Flask(__name__)

# Place your config in app.py
app.config["SECRET_KEY"] = "supersecretkey"
app.config["DEBUG"] = False
# etc.

# The rest of your Flask app code...

# Initialize Extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirects to login page if not authenticated


# ---------- Models ----------
class Config:
    SECRET_KEY = "supersecretkey"
    DEBUG = False
    # ... any other config
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secure_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'  # SQLite Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'manager' or 'user'
    is_active = db.Column(db.Boolean, default=False)

    # Relationships
    products = db.relationship('Product', backref='owner', lazy=True)
    sales = db.relationship('Sale', backref='buyer', lazy=True)
    orders = db.relationship('Order', backref='customer', lazy=True)

    def get_id(self):
        return str(self.id)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    suppliers = db.relationship('Supplier', backref='product', lazy=True)
    sales = db.relationship('Sale', backref='product', lazy=True)
    orders = db.relationship('Order', backref='product_ordered', lazy=True)


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    delivery_time = db.Column(db.Integer, nullable=False)

    # Relationships
    orders = db.relationship('Order', backref='supplier', lazy=True)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'pending', 'approved', 'rejected'


# ---------- User Loader for Flask-Login ----------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- Routes ----------

# Home Route
@app.route('/')
def home():
    logged_in = current_user.is_authenticated
    role = current_user.role if logged_in else None
    return render_template('home.html', logged_in=logged_in, role=role)


# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash("Вы уже вошли в систему.", 'info')
        return redirect(url_for('home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        role = 'user'  # Default role

        if User.query.filter_by(email=email).first():
            flash("Email уже зарегистрирован.", 'danger')
            return render_template('register.html', form=form)

        new_user = User(username=username, email=email, password=password, role=role, is_active=False)
        db.session.add(new_user)
        db.session.commit()
        flash("Регистрация прошла успешно! Ожидайте подтверждения менеджера.", 'success')
        return redirect(url_for('login', role=role))

    return render_template('register.html', form=form)

@app.before_first_request
def create_manager_if_needed():
    manager = User.query.filter_by(email='manager@example.com').first()
    if not manager:
        hashed_pw = generate_password_hash('SecretManagerPass123', method='pbkdf2:sha256')
        manager_user = User(
            username='TheManager',
            email='manager@example.com',
            password=hashed_pw,
            role='manager',
            is_active=True
        )
        db.session.add(manager_user)
        db.session.commit()
        print("Created default manager with password: SecretManagerPass123")
# Login Route
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if current_user.is_authenticated:
        flash("Вы уже вошли в систему.", 'info')
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email, role=role).first()

        if user and check_password_hash(user.password, password):
            if not user.is_active and role == 'user':
                flash("Ваш аккаунт еще не активирован менеджером.", 'warning')
                return render_template('login.html', form=form, role=role)
            login_user(user)
            flash("Вы успешно вошли в систему.", 'success')
            if role == 'manager':
                return redirect(url_for('manager_dashboard'))
            elif role == 'user':
                return redirect(url_for('user_dashboard'))
        else:
            flash("Неверные учетные данные.", 'danger')

    return render_template('login.html', form=form, role=role)


# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы.", 'info')
    return redirect(url_for('home'))


# Manager Dashboard
@app.route('/manager_dashboard')
@login_required
def manager_dashboard():
    if current_user.role != 'manager':
        flash("Доступ запрещен.", 'danger')
        return redirect(url_for('home'))

    users = User.query.filter_by(role='user').all()
    sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    inventory = Product.query.all()
    return render_template('manager_dashboard.html', users=users, sales=sales, inventory=inventory)


# User Dashboard
@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        flash("Доступ запрещен.", 'danger')
        return redirect(url_for('home'))

    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.sale_date.desc()).all()
    products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html', sales=sales, products=products)


# Add Sale
@app.route('/add_sale', methods=['POST'])
@login_required
def add_sale():
    if current_user.role != 'user':
        flash("Доступ запрещен.", 'danger')
        return redirect(url_for('home'))

    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')

    # Input Validation
    if not product_id or not quantity:
        flash("Все поля обязательны для заполнения.", 'danger')
        return redirect(url_for('user_dashboard'))

    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError
    except ValueError:
        flash("Количество должно быть положительным целым числом.", 'danger')
        return redirect(url_for('user_dashboard'))

    product = Product.query.get(product_id)
    if not product:
        flash("Продукт не найден.", 'danger')
        return redirect(url_for('user_dashboard'))

    if product.stock < quantity:
        flash("Недостаточно товара на складе.", 'warning')
        return redirect(url_for('user_dashboard'))

    total_price = product.price * quantity
    product.stock -= quantity

    new_sale = Sale(
        product_id=product_id,
        quantity=quantity,
        total_price=total_price,
        user_id=current_user.id
    )
    db.session.add(new_sale)
    db.session.commit()
    flash("Продажа успешно добавлена.", 'success')
    return redirect(url_for('user_dashboard'))


# Manage Users (Manager Only)
@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'manager':
        flash("Доступ запрещен.", 'danger')
        return redirect(url_for('home'))

    inactive_users = User.query.filter_by(role='user', is_active=False).all()
    active_users = User.query.filter_by(role='user', is_active=True).all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')

        user = User.query.get(user_id)
        if not user or user.role != 'user':
            flash("Пользователь не найден.", 'danger')
            return redirect(url_for('manage_users'))

        if action == 'approve':
            user.is_active = True
            flash(f"Пользователь {user.username} одобрен.", 'success')
        elif action == 'delete':
            db.session.delete(user)
            flash(f"Пользователь {user.username} удален.", 'info')
        else:
            flash("Неверное действие.", 'warning')
            return redirect(url_for('manage_users'))

        db.session.commit()
        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', inactive_users=inactive_users, active_users=active_users)


# Inventory Management
@app.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    if current_user.role not in ['manager', 'user']:
        flash("Доступ запрещен.", 'danger')
        return redirect(url_for('home'))

    form = AddProductForm()
    if form.validate_on_submit():
        name = form.name.data
        price = form.price.data
        stock = form.stock.data
        user_id = current_user.id if current_user.role == 'user' else None  # Assign ownership if user

        new_product = Product(name=name, price=price, stock=stock, user_id=user_id)
        db.session.add(new_product)
        db.session.commit()
        flash("Продукт успешно добавлен в инвентарь.", 'success')
        return redirect(url_for('inventory'))

    if current_user.role == 'user':
        products = Product.query.filter_by(user_id=current_user.id).all()
    else:
        products = Product.query.all()

    return render_template('inventory.html', products=products, form=form)


# Suppliers Management
@app.route('/suppliers', methods=['GET', 'POST'])
@login_required
def suppliers():
    if current_user.role != 'manager':
        flash("Доступ запрещен.", 'danger')
        return redirect(url_for('home'))

    form = AddSupplierForm()
    form.product_id.choices = [(product.id, product.name) for product in Product.query.all()]

    suppliers = Supplier.query.all()

    if form.validate_on_submit():
        product_id = form.product_id.data
        name = form.name.data
        quantity = form.quantity.data
        price = form.price.data
        delivery_time = form.delivery_time.data

        new_supplier = Supplier(
            product_id=product_id,
            name=name,
            quantity=quantity,
            price=price,
            delivery_time=delivery_time
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash("Поставщик успешно добавлен.", 'success')
        return redirect(url_for('suppliers'))

    return render_template('suppliers.html', suppliers=suppliers, form=form)


# Confirm Orders (Manager Only)
@app.route('/confirm_orders', methods=['GET', 'POST'])
@login_required
def confirm_orders():
    if current_user.role != 'manager':
        flash("Доступ запрещен.", 'danger')
        return redirect(url_for('home'))

    orders = Order.query.filter_by(status='pending').all()

    if request.method == 'POST':
        order_id = request.form.get('order_id')
        action = request.form.get('action')

        order = Order.query.get(order_id)
        if not order:
            flash("Заказ не найден.", 'danger')
            return redirect(url_for('confirm_orders'))

        if action == 'approve':
            order.status = 'approved'
            flash("Заказ одобрен.", 'success')
        elif action == 'reject':
            order.status = 'rejected'
            flash("Заказ отклонен.", 'info')
        else:
            flash("Неверное действие.", 'warning')
            return redirect(url_for('confirm_orders'))

        db.session.commit()
        return redirect(url_for('confirm_orders'))

    return render_template('confirm_orders.html', orders=orders)


# Analytics (Manager Only)
@app.route('/analytics', methods=['GET', 'POST'])
@login_required
def analytics():
    if current_user.role != 'manager':
        flash("Доступ запрещен.", 'danger')
        return redirect(url_for('home'))

    form = FilterSalesForm()
    sales_history = []
    total_sales = 0
    total_products_sold = 0
    low_stock_products = Product.query.filter(Product.stock < 10).all()

    if form.validate_on_submit():
        start_date_str = form.start_date.data
        end_date_str = form.end_date.data

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash("Неверный формат даты.", 'danger')
            return redirect(url_for('analytics'))

        sales_history = Sale.query.filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).all()

        total_sales = sum(sale.total_price for sale in sales_history)
        total_products_sold = sum(sale.quantity for sale in sales_history)
    else:
        # Display all sales by default
        sales_history = Sale.query.all()
        total_sales = db.session.query(db.func.sum(Sale.total_price)).scalar() or 0
        total_products_sold = db.session.query(db.func.sum(Sale.quantity)).scalar() or 0

    return render_template(
        'analytics.html',
        form=form,
        total_sales=total_sales,
        total_products_sold=total_products_sold,
        low_stock_products=low_stock_products,
        sales_history=sales_history
    )


# ---------- Error Handlers ----------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# ---------- Run the Application ----------
if __name__ == '__main__':
    app.run(debug=True)
