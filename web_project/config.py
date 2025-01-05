# config.py
import os

# config.py
class Config:
    SECRET_KEY = "supersecretkey"
    DEBUG = False
    # ... any other config
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secure_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'  # SQLite Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
