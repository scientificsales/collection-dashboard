from flask import Flask, render_template, request
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# Google Sheets auth
SERVICE_ACCOUNT_FILE = 'buoyant-keel-455318-e6-987c281d7aae.json'
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.readonly"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Sheet settings
SHEET_NAME = "Collection Plan"

def get_current_sheet():
    month_abbr = datetime.now().strftime("%b")  # e.g., "Mar"
    year_suffix = datetime.now().strftime("%y")  # e.g., "25"
    return f"{month_abbr} {year_suffix}"

def get_customer_data(customer_name, sort_by=None):
    sheet = client.open(SHEET_NAME).worksheet(get_current_sheet())
    all_values = sheet.get_all_values()

    # Use row 2 as headers, rows from 3 onwards as data
    headers = all_values[1]
    data_rows = all_values[2:]

    df = pd.DataFrame(data_rows, columns=headers)

    # Normalize and filter
    df["Customer Name"] = df["Customer Name"].astype(str).str.strip().str.upper()
    customer_name = customer_name.strip().upper()

    df_customer = df[df["Customer Name"].str.contains(customer_name, case=False, na=False)]

    if df_customer.empty:
        return None

    # Convert Expected and Received to numeric
    df_customer["Expected"] = pd.to_numeric(df_customer["Expected"].str.replace(",", "").str.replace("₹", ""), errors='coerce')
    df_customer["Received"] = pd.to_numeric(df_customer["Received"].str.replace(",", "").str.replace("₹", ""), errors='coerce')
    df_customer["Difference"] = df_customer["Expected"] - df_customer["Received"]

    if sort_by == "difference":
        df_customer = df_customer.sort_values(by="Difference", ascending=False)

    expected = df_customer["Expected"].sum()
    received = df_customer["Received"].sum()
    pending = expected - received

    return {
        "customer": customer_name.title(),
        "expected": f"₹{int(expected):,}",
        "received": f"₹{int(received):,}",
        "pending": f"₹{int(pending):,}",
        "rows": df_customer.to_dict(orient="records"),
        "sheet": get_current_sheet()
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        customer = request.form['customer']
        sort_by = request.form.get('sort_by')
        result = get_customer_data(customer, sort_by)
    return render_template("index.html", result=result)

if __name__ == '__main__':
    app.run(debug=True)
