import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os

databaseURL = os.getenv("TRACKER_TELEGRAM_TOKEN")

cred = credentials.Certificate("accounts/firebase_account.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': databaseURL
})
