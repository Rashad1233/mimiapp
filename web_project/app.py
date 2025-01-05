from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, customer, supplier
    is_active = db.Column(db.Boolean, default=False)  # Пользователь активен или нет


class CustomerSupplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Главная страница выбора роли
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/select_role', methods=['POST'])
def select_role():
    role = request.form['role']
    if role == 'admin':
        return redirect(url_for('login', role='admin'))
    elif role == 'customer':
        return redirect(url_for('login', role='customer'))
    elif role == 'supplier':
        return redirect(url_for('login', role='supplier'))
    return "Invalid role selected.", 400


# Вход
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, role=role).first()

        if user and check_password_hash(user.password, password):
            if not user.is_active:
                return "Your account is not yet approved by the admin."
            session['user_id'] = user.id
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'customer':
                return redirect(url_for('customer_dashboard'))
            elif user.role == 'supplier':
                return redirect(url_for('supplier_dashboard'))

        return "Invalid credentials or role."

    return render_template('login.html', role=role)


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method="pbkdf2:sha256")
        role = request.form['role']

        # Проверка уникальности
        if User.query.filter_by(email=email).first():
            return "Email already registered."

        new_user = User(username=username, email=email, password=password, role=role, is_active=False)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login', role=role))

    return render_template('register.html')


# Администратор: просмотр и активация пользователей
@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return "Access denied."

    inactive_users = User.query.filter_by(is_active=False).all()
    return render_template('admin_dashboard.html', inactive_users=inactive_users)


@app.route('/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return "Access denied."

    user = User.query.get(user_id)
    if user:
        user.is_active = True
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return "User not found."


@app.route('/admin/reject/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return "Access denied."

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return "User not found."


# Администратор: просмотр активных пользователей
@app.route('/admin/active_users', methods=['GET', 'POST'])
def active_users():
    if 'role' not in session or session['role'] != 'admin':
        return "Access denied."

    if request.method == 'POST':
        security_key = request.form.get('security_key')
        user_id = request.form.get('user_id')

        # Проверяем ключ безопасности
        if security_key != "UHm8g167":
            return "Invalid security key."

        # Удаляем пользователя
        user = User.query.get(user_id)
        if user and user.is_active:
            db.session.delete(user)
            db.session.commit()
            return redirect(url_for('active_users'))

        return "User not found or not active."

    # Отображаем всех активных пользователей
    active_users = User.query.filter_by(is_active=True).all()
    return render_template('admin_active_users.html', active_users=active_users)


# Клиенты
@app.route('/customer')
def customer_dashboard():
    if 'role' not in session or session['role'] != 'customer':
        return "Access denied."

    suppliers = CustomerSupplier.query.filter_by(customer_id=session['user_id']).all()
    return render_template('customer_dashboard.html', suppliers=suppliers)


# Поставщики
@app.route('/supplier')
def supplier_dashboard():
    if 'role' not in session or session['role'] != 'supplier':
        return "Access denied."

    return render_template('supplier_dashboard.html')


# Выход из системы
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# Функция для создания администратора
def create_admin():
    admin_email = "admin@example.com"
    admin_password = "password123"

    # Проверяем, существует ли уже администратор
    existing_admin = User.query.filter_by(email=admin_email, role="admin").first()
    if not existing_admin:
        admin = User(
            username="admin",
            email=admin_email,
            password=generate_password_hash(admin_password, method="pbkdf2:sha256"),
            role="admin",
            is_active=True  # Администратор активен по умолчанию
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Администратор создан! Email: {admin_email}, Пароль: {admin_password}")
    else:
        print("Администратор уже существует.")


# Создание базы данных
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создание всех таблиц в базе данных
        create_admin()  # Создаём администратора
    app.run(debug=True)
