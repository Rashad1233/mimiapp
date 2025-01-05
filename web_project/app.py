from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=False)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=5)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_standard = db.Column(db.Boolean, default=False)

# Главная страница
@app.route('/')
def home():
    return render_template('login.html', role="manager")

# Вход
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, role=role).first()

        if user and check_password_hash(user.password, password):
            if not user.is_active:
                return "Your account is pending approval by the manager."
            session['user_id'] = user.id
            session['role'] = user.role
            if user.role == 'manager':
                return redirect(url_for('manager_dashboard'))
            elif user.role == 'user':
                return redirect(url_for('user_dashboard'))
        return "Invalid credentials or role."
    return render_template('login.html', role=role)

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method="pbkdf2:sha256")
        role = "user"
        manager_id = request.form.get('manager_id')

        if User.query.filter_by(email=email).first():
            return "Email already registered."

        manager = User.query.get(manager_id)
        if manager and User.query.filter_by(manager_id=manager_id).count() >= USER_LIMIT:
            return "User limit for this manager has been reached."

        new_user = User(username=username, email=email, password=password, role=role, manager_id=manager_id, is_active=False)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login', role="user"))
    return render_template('register.html')

# Панель менеджера
@app.route('/manager')
def manager_dashboard():
    if 'role' not in session or session['role'] != 'manager':
        return "Access denied."

    users = User.query.filter_by(manager_id=session['user_id']).all()
    return render_template('manager_dashboard.html', users=users, user_limit=USER_LIMIT)

# Панель пользователя
@app.route('/user')
def user_dashboard():
    if 'role' not in session or session['role'] != 'user':
        return "Access denied."

    manager_id = User.query.get(session['user_id']).manager_id
    return render_template('user_dashboard.html', manager_id=manager_id)

# Управление инвентарём
@app.route('/manager/inventory', methods=['GET', 'POST'])
def manage_inventory():
    if 'role' not in session or session['role'] != 'manager':
        return "Access denied."

    if request.method == 'POST':
        product_name = request.form['product_name']
        quantity = int(request.form['quantity'])
        min_stock = int(request.form['min_stock'])

        new_item = Inventory(
            product_name=product_name,
            quantity=quantity,
            min_stock=min_stock,
            manager_id=session['user_id']
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('manager_dashboard'))

    inventory_items = Inventory.query.filter_by(manager_id=session['user_id']).all()
    return render_template('inventory.html', inventory_items=inventory_items)

# Выход из системы
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Создание базы данных
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
