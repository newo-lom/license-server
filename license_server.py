# ==========================================================
# 🧩 LICENSE SERVER (MongoDB + Flask)
# Lombardi Print Studio Pro
# ==========================================================
from flask import Flask, request, jsonify
import datetime, os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import random, string

# ==========================================================
# 🔧 INITIALIZATION
# ==========================================================
app = Flask(__name__)
load_dotenv()

# --- MongoDB Configuration ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "license_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
licenses_col = db["licenses"]

# ==========================================================
# 🔑 UTILITY FUNCTIONS
# ==========================================================
def generate_license_key(prefix="DTF", suffix="XYZ"):
    """Generate a professional-style license key (e.g., DTF-9QK2-X8WR-2TLP-XYZ)."""
    parts = ["".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
    return f"{prefix}-{'-'.join(parts)}-{suffix}"

def find_license(license_key):
    return licenses_col.find_one({"license_key": license_key})

def update_license(license_key, data):
    licenses_col.update_one({"license_key": license_key}, {"$set": data})

def insert_license(data):
    licenses_col.insert_one(data)

def delete_license(license_key):
    licenses_col.delete_one({"license_key": license_key})

# ==========================================================
# 🌐 ROUTES
# ==========================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running", "message": "License Server is online"})

# ----------------------------------------------------------
# 🟩 ACTIVATE LICENSE
# ----------------------------------------------------------
@app.route("/activate", methods=["POST"])
def activate():
    payload = request.get_json()
    license_key = payload.get("license_key")
    hwid = payload.get("hwid")

    if not license_key or not hwid:
        return jsonify({"status": "error", "message": "Missing license key or HWID"}), 400

    record = find_license(license_key)
    if not record:
        return jsonify({"status": "error", "message": "Invalid license key"}), 404

    expiry = datetime.datetime.strptime(record["expiry"], "%Y-%m-%d").date()
    if expiry < datetime.date.today():
        return jsonify({"status": "error", "message": "License expired"}), 403

    hwids = record.get("activated_hwids", [])
    max_activations = record.get("max_activations", 1)

    if hwid not in hwids:
        if len(hwids) >= max_activations:
            return jsonify({"status": "error", "message": "Activation limit reached"}), 403
        hwids.append(hwid)
        update_license(license_key, {"activated_hwids": hwids})

    return jsonify({
        "status": "ok",
        "message": "License activated successfully",
        "expiry": record["expiry"],
        "customer": record["customer"]
    })

# ----------------------------------------------------------
# 🟩 VERIFY LICENSE
# ----------------------------------------------------------
@app.route("/verify", methods=["POST"])
def verify():
    payload = request.get_json()
    license_key = payload.get("license_key")
    hwid = payload.get("hwid")

    if not license_key or not hwid:
        return jsonify({"status": "error", "message": "Missing license key or HWID"}), 400

    record = find_license(license_key)
    if not record:
        return jsonify({"status": "error", "message": "Invalid license"}), 404

    expiry = datetime.datetime.strptime(record["expiry"], "%Y-%m-%d").date()
    if expiry < datetime.date.today():
        return jsonify({"status": "error", "message": "License expired"}), 403

    hwids = record.get("activated_hwids", [])
    max_activations = record.get("max_activations", 2)

    if hwid not in hwids:
        if len(hwids) >= max_activations:
            return jsonify({
                "status": "error",
                "message": "Activation limit reached. Please deactivate another device first."
            }), 403
        hwids.append(hwid)
        update_license(license_key, {"activated_hwids": hwids})

    return jsonify({
        "status": "ok",
        "message": "License verified successfully",
        "customer": record.get("customer", "Unknown"),
        "product": record.get("product", "DTF & Screen Printing Manager Pro"),
        "version": record.get("version", "1.0.0"),
        "expiry": record["expiry"],
        "activated_hwids": record.get("activated_hwids", []),
        "max_activations": record.get("max_activations", 2),
        "activations_used": len(record.get("activated_hwids", []))
    })

# ----------------------------------------------------------
# 🟩 DEACTIVATE LICENSE
# ----------------------------------------------------------
@app.route("/deactivate", methods=["POST"])
def deactivate():
    payload = request.get_json()
    license_key = payload.get("license_key")
    hwid = payload.get("hwid")

    if not license_key or not hwid:
        return jsonify({"status": "error", "message": "Missing license key or HWID"}), 400

    record = find_license(license_key)
    if not record:
        return jsonify({"status": "error", "message": "Invalid license key"}), 404

    hwids = record.get("activated_hwids", [])
    if hwid in hwids:
        hwids.remove(hwid)
        update_license(license_key, {"activated_hwids": hwids})
        print(f"🔄 Deactivated HWID {hwid} for license {license_key}")
        return jsonify({
            "status": "ok",
            "message": f"Device {hwid} removed successfully.",
            "remaining_activations": record["max_activations"] - len(hwids)
        })

    return jsonify({
        "status": "error",
        "message": "HWID not found under this license."
    }), 404

# ----------------------------------------------------------
# 🟩 ADMIN: CREATE LICENSE
# ----------------------------------------------------------
@app.route("/create_license", methods=["POST"])
def create_license():
    key = request.args.get("key")
    if key != "Newo_Lomb_DTF_2025":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    payload = request.get_json()
    customer = payload.get("customer")
    expiry = payload.get("expiry")
    max_activations = payload.get("max_activations", 1)
    product = payload.get("product", "DTF & Screen Printing Manager Pro")

    if not customer or not expiry:
        return jsonify({"status": "error", "message": "Missing customer or expiry"}), 400

    license_key = generate_license_key()
    new_license = {
        "license_key": license_key,
        "customer": customer,
        "expiry": expiry,
        "max_activations": max_activations,
        "activated_hwids": [],
        "product": product,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    insert_license(new_license)

    return jsonify({
        "status": "ok",
        "message": "License created successfully",
        "license_key": license_key
    })

# ----------------------------------------------------------
# 🟩 ADMIN: DELETE LICENSE
# ----------------------------------------------------------
@app.route("/delete_license", methods=["POST"])
def delete_license_route():
    data = request.get_json(silent=True) or {}
    license_key = data.get("license_key") or request.args.get("license_key")
    admin_key = request.args.get("key", "")

    if admin_key != "Newo_Lomb_DTF_2025":
        return jsonify({"status": "error", "message": "❌ Unauthorized request"}), 403

    if not license_key:
        return jsonify({"status": "error", "message": "⚠️ Missing license_key"}), 400

    record = find_license(license_key)
    if not record:
        return jsonify({"status": "error", "message": f"License '{license_key}' not found"}), 404

    delete_license(license_key)
    print(f"🗑️ License deleted: {license_key}")

    return jsonify({
        "status": "ok",
        "message": f"✅ License '{license_key}' deleted successfully."
    }), 200

# ==========================================================
# 🚀 RUN SERVER
# ==========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
