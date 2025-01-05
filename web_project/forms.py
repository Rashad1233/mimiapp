# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class AddProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    price = FloatField('Price ($)', validators=[DataRequired(), NumberRange(min=0.01)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Add Product')

class AddSupplierForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    name = StringField('Supplier Name', validators=[DataRequired(), Length(max=100)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    price = FloatField('Price ($)', validators=[DataRequired(), NumberRange(min=0.01)])
    delivery_time = IntegerField('Delivery Time (days)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Supplier')

class FilterSalesForm(FlaskForm):
    start_date = StringField('Start Date', validators=[DataRequired()])  # Consider using DateField with proper format
    end_date = StringField('End Date', validators=[DataRequired()])
    submit = SubmitField('Filter')
