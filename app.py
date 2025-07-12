from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import pandas as pd
import itertools
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import secrets
from fpdf import FPDF
import json
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# -------------------- Google Sheets Setup --------------------
COSTING_SHEET_ID = "1JcMtiFSqjUVUr8dNOi8nCPrKn1Oee628jW4H3eq3Tvk"
COSTING_SHEET_RANGE = "new!A1:Z1000"
MATRIX_SHEET_ID = "1WZdI-VbPaNZ2elgY0DvF0WoTRlqKztCkGrAtYvuk3lU"
MATRIX_SHEET_NAME = "Sheet1"

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


GOOGLE_CREDS = json.loads(os.environ['GOOGLE_CREDS_JSON'])
creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=SCOPES)

#creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
client = gspread.authorize(creds)


def get_credentials():
    info = json.loads(os.environ["GOOGLE_CREDS_JSON"])
    return Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])



def read_price_sheet():
    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets().values().get(
        spreadsheetId=COSTING_SHEET_ID,
        range=COSTING_SHEET_RANGE
    ).execute()
    values = sheet.get("values", [])
    df = pd.DataFrame(values[1:], columns=values[0])
    df.replace("", None, inplace=True)

    for col in ["Rate", "ProRate", "ReRate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    product_rates = {row["Product"]: row["Rate"] for _, row in df.iterrows() if row.get("Product")}

    labour_rate = df.loc[df["Production"] == "Labour", "ProRate"].values[0]
    transport_rate = df.loc[df["Production"] == "Transport (Default: 350)", "ProRate"].values[0]
    indirect_expense_rate = df.loc[df["Production"] == "Indirect & Office expense (Default: 7)", "ProRate"].values[0]
    wastage_rate = df.loc[df["Production"] == "Wastage (Default: 3)", "ProRate"].values[0]

    margin_percent = df.loc[df["Retail"] == "Margin 25%", "ReRate"].values[0]
    tax_percent = df.loc[df["Retail"] == "Tax 18%", "ReRate"].values[0]
    working_cap_percent = df.loc[df["Retail"] == "Working Capital Interest (Default: 5)", "ReRate"].values[0]

    pvc_packing_rate = product_rates.get("PVC Packing", 0)
    flat_packing_cost = product_rates.get("Thread, Cornershoe, Label", 0)

    return (
        product_rates, labour_rate, transport_rate, indirect_expense_rate,
        wastage_rate, margin_percent, tax_percent, working_cap_percent,
        pvc_packing_rate, flat_packing_cost
    )

# -------------------------------------
def calculate_total_cost(length, width, layers, rates, dealer_margin_percent=0):
    (
        product_rates, labour_rate, transport_rate, indirect_expense_rate,
        wastage_rate, margin_percent, tax_percent, working_cap_percent,
        pvc_packing_rate, flat_packing_cost
    ) = rates

    area = length * width
    quilting_thickness = 1
    quilting_rate = product_rates.get("Quilting", 0)

    material_cost = sum(area * thk * product_rates.get(mat, 0) for mat, thk in layers)
    total_thickness = sum(thk for _, thk in layers) + quilting_thickness
    material_cost += area * quilting_thickness * quilting_rate * 2
    material_cost += area * pvc_packing_rate + flat_packing_cost

    total_cost = material_cost + (labour_rate * total_thickness * area) + transport_rate
    total_cost += (indirect_expense_rate * material_cost / 100) + (wastage_rate * material_cost / 100)

    mrp = total_cost * (1 + margin_percent / 100)
    mrp += mrp * (tax_percent / 100) + mrp * (working_cap_percent / 100)
    dealer_price = mrp + (mrp * dealer_margin_percent / 100)

    return round(mrp, 2), round(dealer_price, 2)

# -------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    product_rates, *_ = read_price_sheet()
    material_options = [m for m in product_rates.keys() if m not in ["PVC Packing", "Thread, Cornershoe, Label", "Quilting"]]

    if request.method == "POST":
        length = float(request.form.get("length"))
        width = float(request.form.get("width"))
        dealer_margin = float(request.form.get("dealer_margin") or 0)

        core_layers = []
        for material, thickness in zip(request.form.getlist("core_material"), request.form.getlist("core_thickness")):
            if material and thickness:
                core_layers.append((material, float(thickness)))

        #  Unpack read_price_sheet() correctly
        rates = read_price_sheet()
        product_rates = rates[0]
        constants = {
            "labour_rate": rates[1],
            "transport_rate": rates[2],
            "indirect_expense_rate": rates[3],
            "wastage_rate": rates[4],
            "margin_percent": rates[5],
            "tax_percent": rates[6],
            "working_cap_percent": rates[7],
            "dealer_margin_percent": dealer_margin,  #  User input
            "pvc_packing_rate": rates[8],
            "flat_packing_cost": rates[9]
        }

        #  Now call the function with two separate dicts
        mrp, dealer_price = calculate_total_cost(length, width, core_layers, product_rates, constants)

        details = {
            "Length": f"{length}\"",
            "Width": f"{width}\"",
            "Core Layers": core_layers
        }

        pdf_path = export_pdf(details, mrp)
        return render_template("bill.html", mrp=mrp, dealer_price=dealer_price, pdf_path=pdf_path, details=details)

    return render_template("index.html", materials=material_options)

# -------------------------------------
def export_pdf(details, mrp):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    pdf.cell(200, 10, txt="Mattress Bill", ln=True, align="C")
    pdf.ln(10)

    for key, value in details.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)

    pdf.cell(200, 10, txt=f"Net Rate (MRP): Rs. {mrp}", ln=True)
    output_path = "Mattress_Bill.pdf"
    pdf.output(output_path)
    return output_path

# -------------------------------------
@app.route("/download")
def download():
    return send_file("Mattress_Bill.pdf", as_attachment=True)
# -------------------------------------
# -------------------- Costing Constants --------------------
def load_rates_and_constants():
    sheet = client.open_by_key(COSTING_SHEET_ID).worksheet("new")
    data = sheet.get_all_values()

    product_rates = {}
    for row in data[1:]:
        product = row[2].strip() if len(row) > 2 else ""
        rate = row[3].strip() if len(row) > 3 else ""
        if product and rate:
            try:
                product_rates[product] = float(rate)
            except ValueError:
                continue

    constants = {
        "labour_rate": 0.0,
        "transport_rate": 0.0,
        "indirect_expense_rate": 0.0,
        "wastage_rate": 0.0,
        "margin_percent": 0.0,
        "tax_percent": 0.0,
        "working_cap_percent": 0.0,
        "dealer_margin_percent": 0.0,
        "pvc_packing_rate": product_rates.get("PVC Packing", 0),
        "flat_packing_cost": product_rates.get("Thread, Cornershoe, Label", 0)
    }

    for row in data:
        if len(row) >= 6:
            label, rate = row[4].strip(), row[5].strip()
            try:
                if label == "Labour":
                    constants["labour_rate"] = float(rate)
                elif "Transport" in label:
                    constants["transport_rate"] = float(rate)
                elif "Indirect" in label:
                    constants["indirect_expense_rate"] = float(rate)
                elif "Wastage" in label:
                    constants["wastage_rate"] = float(rate)
            except ValueError:
                pass

        if len(row) >= 10:
            label, rate = row[8].strip(), row[9].strip()
            try:
                if "Margin" in label:
                    constants["margin_percent"] = float(rate)
                elif "Tax" in label:
                    constants["tax_percent"] = float(rate)
                elif "Working Capital" in label:
                    constants["working_cap_percent"] = float(rate)
                elif "Dealer" in label:
                    constants["dealer_margin_percent"] = float(rate)
            except ValueError:
                pass

    return product_rates, constants

quilting_thickness = 1
mattress_combinations = [
    [("Coir", 1.0), ("EP Foam", 2.0), ("Coir", 1.0)],
    [("Coir", 1.0), ("Foam - Rebonded", 2.0), ("Coir", 1.0)],
    [("Coir 80D", 4.0)],
    [("Coir", 2.0), ("Single Foam", 2.0)],
    [("Coir", 1.0), ("Foam - Rebonded", 2.0), ("Coir", 2.0)],
    [("Coir 100D", 5.0)],
    [("Coir", 1.0), ("Foam - Rebonded", 2.0), ("Coir", 1.0), ("Topper", 1.0)],
    [("PU Foam", 2.0), ("Coir", 2.0)],
    [("Coir", 2.0), ("Foam - Rebonded", 2.0), ("Natural Latex", 2.0)],
    [("Pocketed (only 5) Spring", 5.0), ("Coir", 1.0)],
    [("Pocketed (only 5) Spring", 5.0), ("Foam - Rebonded", 2.0), ("Single Foam (mm)", 0.0)],
    [("Bonnel (only 5) Spring", 5.0), ("Coir", 1.0)],
    [("Coir", 2.0), ("Foam - Rebonded", 2.0), ("Memory Foam", 2.0)],
    [("Topper (Memory Foam)", 1.0)],
    [("Topper (Natural Latex)", 1.0)]
]



length_options = [72, 75, 78]
width_options = [30, 36, 60, 72]

# -------------------- Write to Google Sheet --------------------
def write_to_google_sheet(df, sheet_id, sheet_name):
    
    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# -------------------- Routes --------------------
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=1)
app.config['SESSION_PERMANENT'] = True


@app.route('/customize')
def customize():
    session.setdefault('layers', [])
    session.setdefault('products', [])
    session.setdefault('sizes', [])
    product_rates, _ = load_rates_and_constants()
    return render_template("customize.html", materials=list(product_rates.keys()))

@app.route('/add-layer', methods=["POST"])
def add_layer():
    data = request.get_json()
    material = data.get("material")
    thickness = float(data.get("thickness", 0))
    product_rates, _ = load_rates_and_constants()
    if material not in product_rates or thickness <= 0:
        return jsonify({"error": "Invalid input"}), 400
    session['layers'].append((material, thickness))
    session.modified = True
    session.permanent = True
    return jsonify({"layers": session['layers']})

@app.route('/finalize-product', methods=["POST"])
def finalize_product():
    if not session['layers']:
        return jsonify({"error": "No layers added"}), 400
    session['products'].append(session['layers'])
    session['layers'] = []
    session.modified = True
    return jsonify({"products": session['products']})

@app.route('/add-size', methods=["POST"])
def add_size():
    data = request.get_json()
    length = float(data.get("length", 0))
    width = float(data.get("width", 0))
    if length <= 0 or width <= 0:
        return jsonify({"error": "Invalid size"}), 400
    session['sizes'].append((length, width))
    session.modified = True
    return jsonify({"sizes": session['sizes']})

@app.route('/generate', methods=["GET"])
def generate():
    product_rates, constants = load_rates_and_constants()
    products = session.get('products', [])
    sizes = session.get('sizes', [])

    columns = ["Length", "Width"]
    for prod in products:
        desc = " + ".join([f"{mat} {thk}\"" for mat, thk in prod])
        columns += [f"{desc} | Net Rate", f"{desc} | MRP"]
    for combo in mattress_combinations:
        #desc = " + ".join([f"{mat} {thk}\"" for mat, thk in combo])
        desc = " + ".join([f"{mat} {thk}\"" for item in combo if isinstance(item, (list, tuple)) and len(item) == 2 for mat, thk in [item]])
        columns += [f"{desc} | Net Rate", f"{desc} | MRP"]

    all_lengths = sorted(set(length_options + [l for l, _ in sizes]))
    all_widths = sorted(set(width_options + [w for _, w in sizes]))
    data = []
    for length, width in itertools.product(all_lengths, all_widths):
        row = [length, width]
        for prod in products:
            mrp, dealer_price = calculate_total_cost(length, width, prod, product_rates, constants)
            row += [dealer_price, mrp]
        for combo in mattress_combinations:
            if not all(isinstance(layer, (list, tuple)) and len(layer) == 2 for layer in combo):
                continue
            mrp, dealer_price = calculate_total_cost(length, width, combo, product_rates, constants)
            row += [dealer_price, mrp]
        data.append(row)

    df = pd.DataFrame(data, columns=columns)
    write_to_google_sheet(df, MATRIX_SHEET_ID, MATRIX_SHEET_NAME)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{MATRIX_SHEET_ID}/edit#gid=0"
    return jsonify({"message": "Sheet updated successfully", "url": sheet_url})

# -------------------- Costing Calculation --------------------
def calculate_total_cost(length, width, layers, product_rates, constants):
    area = length * width
    material_cost = sum(area * thk * product_rates.get(mat, 0) for mat, thk in layers)
    total_thickness = sum(thk for _, thk in layers) + quilting_thickness
    quilting_rate = product_rates.get("Quilting", 0)
    material_cost += area * quilting_thickness * quilting_rate * 2
    material_cost += area * constants["pvc_packing_rate"] + constants["flat_packing_cost"]
    total_cost = material_cost + (constants["labour_rate"] * total_thickness * area) + constants["transport_rate"]
    total_cost += (constants["indirect_expense_rate"] * material_cost / 100) + (constants["wastage_rate"] * material_cost / 100)
    mrp = total_cost * (1 + constants["margin_percent"] / 100)
    mrp += mrp * (constants["tax_percent"] / 100) + mrp * (constants["working_cap_percent"] / 100)
    dealer_price = mrp + (mrp * constants["dealer_margin_percent"] / 100)
    return round(mrp, 2), round(dealer_price, 2)

# -------------------- Run App --------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
