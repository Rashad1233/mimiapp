# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secure_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'  # SQLite Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
