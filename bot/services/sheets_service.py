"""Read member records from the Google Sheet."""
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import settings
from config.constants import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEETS_SCOPES


def fetch_sheet_data():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEETS_SCOPES
    )
    client = gspread.authorize(credentials)
    worksheet = client.open_by_url(settings.gsheet_url).get_worksheet(0)
    return worksheet.get_all_records()
