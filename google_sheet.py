from google.oauth2 import service_account
from googleapiclient.discovery import build
from common import EntryType
import datetime as dt

# Path to the downloaded JSON key file
SERVICE_ACCOUNT_FILE = 'accounts/service_account.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheets_api = build('sheets', 'v4', credentials=creds)

# Dropdown range
transport_range = ["Dropdown!A3:A9"]
others_sub_range = [f"Dropdown!{chr(i)}2:{chr(i)}9" for i in range(ord('B'), ord('K'))]
others_main_range = ["Dropdown!A2:J2"]
payment_sub_range = [f"Dropdown!{chr(i)}12:{chr(i)}19" for i in range(ord('A'), ord('K'))]
payment_main_range = ["Dropdown!A12:J12"]

# Get the main dropdown values
def get_main_dropdown_value(sheet_id, entry_type):
    range = []
    if entry_type == EntryType.TRANSPORT:
        range = transport_range
    elif entry_type == EntryType.OTHERS:
        range = others_main_range
    else:
        range = payment_main_range
    # Make the request
    results = sheets_api.spreadsheets().values().batchGet(
        spreadsheetId=sheet_id,
        ranges=range).execute()

    # Get the values from the result
    value_ranges = results.get('valueRanges', [])
    
    dropdown = []
    for value in value_ranges:
        dropdown.append(value.get('values', []))

    if entry_type == EntryType.TRANSPORT:
        new_list = list(dropdown[0])
        flat_list = [item for sublist in new_list for item in sublist]
        return flat_list
    return dropdown[0][0]

# Get the sub dropdown values
def get_sub_dropdown_value(sheet_id, main_value, entry_type):
    range = []
    if entry_type == EntryType.OTHERS:
        range = others_sub_range
    else:
        range = payment_sub_range
    # Make the request
    results = sheets_api.spreadsheets().values().batchGet(
        spreadsheetId=sheet_id,
        ranges=range).execute()

    # Get the values from the result
    value_ranges = results.get('valueRanges', [])
    
    dropdown = []
    for value in value_ranges:
        if value.get('values', []):
            if main_value == value.get('values', [])[0][0]:
                dropdown.append(value.get('values', []))
                pass

    flat_list = [item for sublist in dropdown[0] for item in sublist]
    return flat_list

# Sum up previous day
def update_prev_day(sheet_id, month, first_row):
    last_row = get_new_row(sheet_id, month)
    # Write the message to the Google Sheet
    body = {'values': [[f'=SUM(C{first_row}:H{last_row})']]}
    range_name = f'{month}!B{first_row}'
    sheets_api.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body).execute()

# Get new row no in sheets
def get_new_row(sheet_id, month):
    result = sheets_api.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f'{month}!A:K').execute()
    values = result.get('values', [])
    return len(values)

# Enter new date into cell
def create_date(sheet_id, day, month, first_row):
    # Update date in column A
    body = {'values': [[day]]}
    range_name = f'{month}!A{first_row}'
    sheets_api.spreadsheets().values().update(
    spreadsheetId=sheet_id,
    range=range_name,
    valueInputOption='USER_ENTERED',
    body=body).execute()

# create new entry into google sheet
def create_entry(sheet_id, month, row_tracker, row_data):
    entry_type = row_data[0]
    price = row_data[1].strip()
    remarks = row_data[2].strip()
    category = row_data[3].strip()
    payment = row_data[4].strip()

    data = [price, remarks, category, payment]
    sheet_column_start = 'H'
    sheet_column_end = 'K'
    if entry_type == EntryType.TRANSPORT:
        remarks_list = [remark.strip() for remark in remarks.split(',')]
        sheet_column_start = 'C'
        sheet_column_end = 'G'
        data = [price] + remarks_list + [category, payment]

    # Write the message to the Google Sheet
    body = {'values': [data]}
    range_name = f'{month}!{sheet_column_start}{row_tracker}:{sheet_column_end}{row_tracker}'
    sheets_api.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body).execute()
    
def get_trackers(sheet_id):
    result = sheets_api.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f'Tracker!B3:E3').execute()
    values = result.get('values', [])
    return values[0]

def update_rows(sheet_id, day, new_row):
    values = [[day] + [new_row] * 3]  # Create a row with the same value repeated 3 times
    range_name = 'Tracker!B3:E3'
    body = {'values': values}
    request = sheets_api.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body
    )
    request.execute()


def row_incremental(sheet_id, entry_type):
    range_name = 'Tracker!B3:E3'
    response = sheets_api.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_name,
        majorDimension='ROWS'
    ).execute()

    values = response.get('values', [])
    if values:
        row_values = values[0]
        if entry_type == EntryType.OTHERS:
            row_values[1] = str(int(row_values[1]) + 1)  # Increment others count
        elif entry_type == EntryType.TRANSPORT:
            row_values[2] = str(int(row_values[2]) + 1)  # Increment transport count

        body = {'values': [row_values]}
        sheets_api.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()

def get_quick_add_settings(sheet_id, entry_type):
    range_name = 'Tracker!G3:J3'  # Replace with the desired range in your Google Sheet
    response = sheets_api.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_name,
        majorDimension='ROWS'
    ).execute()

    values = response.get('values', [])
    if values:
        if entry_type == EntryType.TRANSPORT:
            transport_payment = values[0][0] if len(values[0]) > 0 else None
            transport_type = values[0][1] if len(values[0]) > 1 else None
            return transport_payment, transport_type
        else:
            others_payment = values[0][2] if len(values[0]) > 2 else None
            others_type = values[0][3] if len(values[0]) > 3 else None
            return others_payment, others_type

    return None

def update_quick_add_settings(sheet_id, entry_type, payment, type):
    range_name = 'Tracker!G3:J3'  # Replace with the desired range in your Google Sheet

    # Get existing values from the range, or an empty list if the range is empty
    response = sheets_api.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_name,
        majorDimension='ROWS'
    ).execute()

    values = response.get('values', [])  # Initialize with an empty list if no values are present

    if not values:
        values = [[]]  # Create an empty row if the range is empty

    if len(values) == 0:
        values.append([])  # Add a row if the values list is empty

    # Determine the number of columns needed
    num_columns = max(4, len(values[0]))

    if len(values[0]) < num_columns:
        values[0].extend([''] * (num_columns - len(values[0])))  # Extend the existing row with empty strings

    if entry_type == EntryType.TRANSPORT:
        values[0][0] = payment if payment else ''
        values[0][1] = type if type else ''
    else:
        values[0][2] = payment if payment else ''
        values[0][3] = type if type else ''

    body = {'values': values}
    sheets_api.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()

    return True