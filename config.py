
import os

class Config:
    SECRET_KEY = 'your_secret_key_here'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:password@localhost/recipe_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
