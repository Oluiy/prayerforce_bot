import os
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

def fetch_sheet_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)


    sheet_url = os.getenv("GSHEET_URL", "https://docs.google.com/spreadsheets/d/13TBoRvSj-0Vpc0-WQQYNYbnZa-ywzQ9dBanszT9KMvk/edit?usp=sharing")
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.get_worksheet(0) 
    records = worksheet.get_all_records()
    return records
