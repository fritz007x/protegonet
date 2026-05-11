import json
import pandas as pd
import numpy as np
from faker import Faker
import uuid
from datetime import datetime, timedelta

# -----------------------------
# CONFIG
# -----------------------------
SEED = 42
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

N_PROVIDERS = 20
N_INVOICES = 300
MAX_ITEMS = 5
START_DATE = datetime(2026, 1, 1)

TAX_RATE = 0.15
FRAUD_RATE = 0.1  # 10% fraud

# -----------------------------
# HELPER: Generate bank account
# -----------------------------
def generate_bank_account():
    return fake.bban()  # realistic bank account number

# -----------------------------
# PROVIDERS
# -----------------------------
providers = []
for _ in range(N_PROVIDERS):
    providers.append({
        "provider_id": str(uuid.uuid4()),
        "country": fake.country_code(),
        "base_price": np.random.uniform(200, 800),
        "bank_account": generate_bank_account()
    })

providers_df = pd.DataFrame(providers)

# -----------------------------
# ITEM POOL
# -----------------------------
ITEM_NAMES = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]

# -----------------------------
# GENERATE INVOICES
# -----------------------------
invoices = []
line_items = []

for i in range(N_INVOICES):

    provider = providers_df.sample(1).iloc[0]
    invoice_id = f"INV_{str(i).zfill(6)}"

    # Date goes backwards from 2026
    days_back = np.random.randint(0, 365)
    invoice_date = START_DATE - timedelta(days=int(days_back))

    n_items = np.random.randint(2, MAX_ITEMS + 1)

    subtotal = 0

    for j in range(n_items):
        qty = np.random.randint(1, 10)

        unit_price = np.random.normal(provider["base_price"], 100)
        unit_price = max(50, round(unit_price, 2))

        line_total = round(qty * unit_price, 2)
        subtotal += line_total

        line_items.append({
            "invoice_id": invoice_id,
            "item": ITEM_NAMES[j],
            "quantity": qty,
            "unit_price": unit_price,
            "line_total": line_total
        })

    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)

    invoices.append({
        "invoice_id": invoice_id,
        "provider_id": provider["provider_id"],
        "country": provider["country"],
        "invoice_date": invoice_date,
        "payment_terms": np.random.choice(["NET30", "NET60", "NET90"], p=[0.6,0.3,0.1]),
        "bank_account": provider["bank_account"],  # ✅ NEW FIELD
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "total": total,
        "is_fraud": 0,
        "fraud_type": "NONE"
    })

# -----------------------------
# INJECT FRAUD
# -----------------------------
fraud_indices = np.random.choice(range(N_INVOICES), int(N_INVOICES * FRAUD_RATE), replace=False)

for idx in fraud_indices:
    fraud_type = np.random.choice(["INFLATED", "DUPLICATE", "QUANTITY", "ACCOUNT_CHANGE"])

    invoices[idx]["is_fraud"] = 1
    invoices[idx]["fraud_type"] = fraud_type

    inv_id = invoices[idx]["invoice_id"]

    if fraud_type == "INFLATED":
        for li in line_items:
            if li["invoice_id"] == inv_id:
                li["unit_price"] *= np.random.uniform(1.5, 3)
                li["line_total"] = round(li["unit_price"] * li["quantity"], 2)

    elif fraud_type == "QUANTITY":
        for li in line_items:
            if li["invoice_id"] == inv_id:
                li["quantity"] *= np.random.randint(3, 6)
                li["line_total"] = round(li["unit_price"] * li["quantity"], 2)

    elif fraud_type == "DUPLICATE":
        duplicate = invoices[idx].copy()
        duplicate["invoice_id"] = duplicate["invoice_id"] + "_DUP"
        invoices.append(duplicate)

    elif fraud_type == "ACCOUNT_CHANGE":
        # 🔴 Simulate bank account fraud
        invoices[idx]["bank_account"] = generate_bank_account()

# -----------------------------
# RECOMPUTE TOTALS AFTER FRAUD
# -----------------------------
line_items_df = pd.DataFrame(line_items)

for inv in invoices:
    inv_id = inv["invoice_id"]
    subset = line_items_df[line_items_df["invoice_id"] == inv_id]

    if len(subset) > 0:
        subtotal = round(subset["line_total"].sum(), 2)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)

        inv["subtotal"] = subtotal
        inv["tax"] = tax
        inv["total"] = total

# -----------------------------
# SAVE DATA (JSONL WITH LINE ITEMS)
# -----------------------------
invoices_df = pd.DataFrame(invoices)
line_items_df = pd.DataFrame(line_items)

# Convert date to string
invoices_df["invoice_date"] = invoices_df["invoice_date"].astype(str)

# Group line items by invoice_id
line_items_grouped = line_items_df.groupby("invoice_id").apply(
    lambda x: x.drop("invoice_id", axis=1).to_dict(orient="records")
).to_dict()

# Write JSONL
with open("invoices.jsonl", "w") as f:
    for _, row in invoices_df.iterrows():
        inv = row.to_dict()
        inv["line_items"] = line_items_grouped.get(inv["invoice_id"], [])
        f.write(json.dumps(inv) + "\n")

print("Dataset generated:")
print(f"- Providers: {len(providers_df)}")
print(f"- Invoices: {len(invoices_df)}")
print(f"- Line items: {len(line_items_df)}")
print("Output file: invoices.jsonl")