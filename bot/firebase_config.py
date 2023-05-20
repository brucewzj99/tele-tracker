import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os

DATABASE_URL = os.getenv("DATABASE_URL")

cred = credentials.Certificate("accounts/firebase_account.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': DATABASE_URL
})