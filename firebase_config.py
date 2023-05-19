import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os

databaseURL = os.getenv("DATABASE_URL")

cred = credentials.Certificate("accounts/firebase_account.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': databaseURL
})
