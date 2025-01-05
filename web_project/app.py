from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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
    is_active = db.Column(db.Boolean, default=False)  # Указывает, активен ли пользователь

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False)  # Дата продажи

    # Связь с моделью Product
    product = db.relationship('Product', backref='sales')




class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    products_offered = db.Column(db.String(200), nullable=False)
    delivery_time = db.Column(db.Integer, nullable=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'pending', 'approved', 'rejected'

# ---------- Вспомогательные функции ----------
def add_test_data():
    with app.app_context():
        if not User.query.filter_by(email="manager@example.com").first():
            manager = User(
                username="Manager1",
                email="manager@example.com",
                password=generate_password_hash("manager123", method='pbkdf2:sha256'),
                role="manager",
                is_active=True
            )
            db.session.add(manager)

        if not Product.query.filter_by(name="Product1").first():
            product = Product(name="Product1", price=10.0, stock=50)
            db.session.add(product)

        if not Supplier.query.filter_by(name="Supplier1").first():
            supplier = Supplier(name="Supplier1", products_offered="Product1, Product2", delivery_time=3)
            db.session.add(supplier)
        with app.app_context():
            sale1 = Sale(
                product_id=1,  # ID продукта
                quantity=10,
                total_price=100.0,
                user_id=1,  # ID пользователя
                supplier_id=1,  # ID поставщика
                sale_date=datetime.now()
            )
            sale2 = Sale(
                product_id=2,
                quantity=5,
                total_price=50.0,
                user_id=2,
                supplier_id=1,
                sale_date=datetime.now()
            )
            db.session.add_all([sale1, sale2])
            db.session.commit()
        db.session.commit()
        print("Тестовые данные добавлены!")

# ---------- Главная страница ----------
@app.route('/')
def home():
    logged_in = 'user_id' in session
    role = session.get('role') if logged_in else None
    return render_template('home.html', logged_in=logged_in, role=role)

# ---------- Регистрация ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    USER_LIMIT = 10  # Лимит активных пользователей

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        role = 'user'

        active_users_count = User.query.filter_by(role='user', is_active=True).count()
        if active_users_count >= USER_LIMIT:
            flash("Достигнут лимит активных пользователей. Регистрация невозможна.")
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash("Email уже зарегистрирован.")
            return render_template('register.html')

        new_user = User(username=username, email=email, password=password, role=role, is_active=False)
        db.session.add(new_user)
        db.session.commit()
        flash("Регистрация прошла успешно! Ожидайте подтверждения менеджера.")
        return redirect(url_for('login', role=role))

    return render_template('register.html')

@app.route('/confirmed_orders', methods=['GET'])
def confirmed_orders():
    if 'user_id' not in session or session['role'] not in ['manager', 'user']:
        return redirect(url_for('home'))

    # У менеджера: все подтвержденные заказы
    if session['role'] == 'manager':
        confirmed_orders = Order.query.filter_by(status='approved').all()
    else:
        # У пользователя: только свои подтвержденные заказы
        confirmed_orders = Order.query.filter_by(user_id=session['user_id'], status='approved').all()

    return render_template('confirmed_orders.html', orders=confirmed_orders)
# ---------- Вход ----------
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Логируем входные данные
        print(f"Попытка входа: email={email}, role={role}")

        # Проверяем, существует ли пользователь с таким email и ролью
        user = User.query.filter_by(email=email, role=role).first()
        print(f"Найден пользователь: {user}")

        if user and check_password_hash(user.password, password):
            # Сохраняем данные в сессии
            session['user_id'] = user.id
            session['role'] = user.role
            print(f"Успешный вход: user_id={user.id}, role={user.role}")

            # Перенаправляем на соответствующую панель
            if role == 'manager':
                return redirect(url_for('manager_dashboard'))
            elif role == 'user':
                return redirect(url_for('user_dashboard'))

        # Если данные неверные, выводим ошибку
        flash("Неверные учетные данные.")
        print("Авторизация не удалась.")
    return render_template('login.html', role=role)


# ---------- Выход ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Вы вышли из системы.")
    return redirect(url_for('home'))

# ---------- Панель менеджера ----------
@app.route('/manager_dashboard')
@app.route('/manager_dashboard')
def manager_dashboard():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('home'))

    # Получаем все продажи
    sales = Sale.query.all()

    # Суммарная статистика
    total_revenue = sum(sale.total_price for sale in sales)
    total_products_sold = sum(sale.quantity for sale in sales)

    return render_template(
        'manager_dashboard.html',
        sales=sales,
        total_revenue=total_revenue,
        total_products_sold=total_products_sold
    )


@app.route('/confirm_users', methods=['GET', 'POST'])
def confirm_users():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('home'))

    # Получаем неактивных пользователей
    inactive_users = User.query.filter_by(role='user', is_active=False).all()
    # Получаем активных пользователей
    active_users = User.query.filter_by(role='user', is_active=True).all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')  # 'approve' или 'delete'
        user = User.query.get(user_id)

        if user:
            if action == 'approve':
                # Утверждаем пользователя
                user.is_active = True
                db.session.commit()
                flash(f"Пользователь {user.username} утверждён.")
            elif action == 'delete':
                # Удаляем пользователя
                db.session.delete(user)
                db.session.commit()
                flash(f"Пользователь {user.username} удалён.")

        return redirect(url_for('confirm_users'))

    return render_template('confirm_users.html', inactive_users=inactive_users, active_users=active_users)

# ---------- Управление пользователями ----------
@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('home'))

    inactive_users = User.query.filter_by(role='user', is_active=False).all()
    active_users = User.query.filter_by(role='user', is_active=True).all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        user = User.query.get(user_id)

        if user:
            if action == 'approve':
                user.is_active = True
                db.session.commit()
                flash(f"Пользователь {user.username} утверждён.")
            elif action == 'delete':
                db.session.delete(user)
                db.session.commit()
                flash(f"Пользователь {user.username} удалён.")

        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', inactive_users=inactive_users, active_users=active_users)

# ---------- Панель пользователя ----------
@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('home'))
    user = User.query.get(session['user_id'])
    products = Product.query.all()
    suppliers = Supplier.query.all()
    return render_template('user_dashboard.html', user=user, products=products, suppliers=suppliers)

# ---------- Управление инвентарем ----------
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        new_product = Product(name=name, price=price, stock=stock)
        db.session.add(new_product)
        db.session.commit()
        flash("Продукт успешно добавлен в инвентарь.")
        return redirect(url_for('inventory'))
    products = Product.query.all()
    return render_template('inventory.html', products=products)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('home'))
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        flash("Продукт успешно удалён.")
    return redirect(url_for('inventory'))

# ---------- Заказы ----------
@app.route('/shopping_cart', methods=['GET', 'POST'])
def shopping_cart():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('home'))

    products = Product.query.all()
    suppliers = Supplier.query.all()
    recommended_supplier = None

    if request.method == 'POST':
        product_id = int(request.form['product_id'])
        quantity = int(request.form['quantity'])

        # Логика автоматического предложения поставщика
        best_supplier = None
        for supplier in suppliers:
            if str(product_id) in supplier.products_offered:
                if not best_supplier or supplier.delivery_time < best_supplier.delivery_time:
                    best_supplier = supplier

        supplier_id = best_supplier.id if best_supplier else int(request.form['supplier_id'])

        # Создаём заказ
        new_order = Order(
            user_id=session['user_id'],
            product_id=product_id,
            supplier_id=supplier_id,
            quantity=quantity,
            status='pending'
        )
        db.session.add(new_order)
        db.session.commit()
        flash("Заказ добавлен в корзину.")

    return render_template('shopping_cart.html', products=products, suppliers=suppliers)


@app.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('home'))

    # Получаем список поставщиков
    suppliers = Supplier.query.all()

    if request.method == 'POST':
        name = request.form['name']
        products_offered = request.form['products_offered']
        delivery_time = int(request.form['delivery_time'])

        # Добавляем нового поставщика
        new_supplier = Supplier(name=name, products_offered=products_offered, delivery_time=delivery_time)
        db.session.add(new_supplier)
        db.session.commit()
        flash("Поставщик успешно добавлен.")

    return render_template('suppliers.html', suppliers=suppliers)

# ---------- Аналитика ----------
@app.route('/analytics')
def analytics():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('home'))

    sales = Sale.query.all()
    total_revenue = sum(sale.total_price for sale in sales)
    total_products_sold = sum(sale.quantity for sale in sales)
    average_order_value = total_revenue / total_products_sold if total_products_sold > 0 else 0
    average_delivery_time = sum(sale.delivery_time for sale in sales) / len(sales) if sales else 0

    return render_template(
        'analytics.html',
        total_revenue=total_revenue,
        total_products_sold=total_products_sold,
        average_order_value=average_order_value,
        average_delivery_time=average_delivery_time
    )


# ---------- Подтверждение заказов ----------
@app.route('/confirm_orders', methods=['GET', 'POST'])
def confirm_orders():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('home'))

    if request.method == 'POST':
        order_id = request.form['order_id']
        action = request.form['action']
        order = Order.query.get(order_id)

        if action == 'approve':
            order.status = 'approved'

            # Автоматическое добавление в продажи
            sale = Sale(
                product_id=order.product_id,
                quantity=order.quantity,
                total_price=order.quantity * Product.query.get(order.product_id).price,
                user_id=order.user_id,
                supplier_id=order.supplier_id,
                delivery_time=Supplier.query.get(order.supplier_id).delivery_time
            )
            db.session.add(sale)
            flash("Заказ подтвержден и добавлен в продажи.")
        elif action == 'reject':
            order.status = 'rejected'
            flash("Заказ отклонён.")

        db.session.commit()

    pending_orders = Order.query.filter_by(status='pending').all()
    return render_template('confirm_orders.html', orders=pending_orders)


# ---------- Запуск приложения ----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаём таблицы, если их ещё нет
        add_test_data()  # Добавляем тестовые данные, если их нет
    app.run(debug=True)
