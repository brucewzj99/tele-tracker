# Import module
import sqlite3
import datetime as dt

# build connection to database
def connect_to_db():
	conn = sqlite3.connect('user-tele.db')
	return conn

# creating table, first time use only
def first_time_only():
	with connect_to_db() as conn:
		cursor = conn.cursor()
		
		user_table = '''CREATE TABLE IF NOT EXISTS user_table(
		telegram_id VARCHAR(255) PRIMARY KEY, 
		sheet_id VARCHAR(255));'''
		cursor.execute(user_table)

# drop table
def drop_table():
	with connect_to_db() as conn:
		cursor = conn.cursor()
		cursor.execute("DROP TABLE IF EXISTS user_table;")

# first time user, create db records
def new_user_setup(telegram_id, sheet_id):
	with connect_to_db() as conn:
		cursor = conn.cursor()
		day = dt.datetime.now().day
		cursor.execute("INSERT OR REPLACE INTO user_table(telegram_id, sheet_id) VALUES (?, ?);", (telegram_id, sheet_id))
		cursor.execute("INSERT OR REPLACE INTO tracker_table(telegram_id, transport_row_tracker, other_row_tracker, day_row_tracker, first_row) VALUES (?, ?, ?, ?, ?);", (telegram_id, day, 5, 5, 5))
		conn.commit()
		return cursor.lastrowid

# check if user exists
def check_if_user_exists(telegram_id):
	with connect_to_db() as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT * FROM user_table WHERE telegram_id = ?", (telegram_id,))
		return bool(cursor.fetchone())

# get user sheet id
def get_user_sheet_id(telegram_id):
	with connect_to_db() as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT sheet_id FROM user_table WHERE telegram_id = ?", (telegram_id,))
		return cursor.fetchone()[0]
