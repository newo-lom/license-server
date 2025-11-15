from flask import Flask, request, jsonify
import json, os, datetime

app = Flask(__name__)

LICENSE_DB = os.path.join(os.path.dirname(__file__), "licenses.json")




# === Utility Functions ===
def load_db():
    if not os.path.exists(LICENSE_DB):
        with open(LICENSE_DB, "w") as f:
            json.dump({}, f)
    with open(LICENSE_DB, "r") as f:
        return json.load(f)

def save_db(data):
    """Save the license database to a persistent location (works with Render Disks)."""
    # ✅ If using a Render Disk, ensure the /data folder exists
    os.makedirs(os.path.dirname(LICENSE_DB), exist_ok=True)

    try:
        with open(LICENSE_DB, "w") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Saved updated license database: {LICENSE_DB}")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"❌ Error saving license database: {e}")


# === API Endpoints ===
@app.route("/activate", methods=["POST"])
def activate():
    payload = request.get_json()
    license_key = payload.get("license_key")
    hwid = payload.get("hwid")

    if not license_key or not hwid:
        return jsonify({"status": "error", "message": "Missing license key or HWID"}), 400

    db = load_db()
    if license_key not in db:
        return jsonify({"status": "error", "message": "Invalid license key"}), 404

    record = db[license_key]

    # Check expiry
    expiry = datetime.datetime.strptime(record["expiry"], "%Y-%m-%d").date()
    if expiry < datetime.date.today():
        return jsonify({"status": "error", "message": "License expired"}), 403

    hwids = record.get("activated_hwids", [])
    max_activations = record.get("max_activations", 1)

    if hwid not in hwids:
        if len(hwids) >= max_activations:
            return jsonify({"status": "error", "message": "Activation limit reached"}), 403
        hwids.append(hwid)
        record["activated_hwids"] = hwids
        db[license_key] = record
        save_db(db)

    return jsonify({
        "status": "ok",
        "message": "License activated successfully",
        "expiry": record["expiry"],
        "customer": record["customer"]
    })


@app.route("/verify", methods=["POST"])
def verify():
    payload = request.get_json()
    license_key = payload.get("license_key")
    hwid = payload.get("hwid")

    if not license_key or not hwid:
        return jsonify({"status": "error", "message": "Missing license key or HWID"}), 400

    db = load_db()
    if license_key not in db:
        return jsonify({"status": "error", "message": "Invalid license"}), 404

    record = db[license_key]
    expiry = datetime.datetime.strptime(record["expiry"], "%Y-%m-%d").date()

    # --- Check expiry
    if expiry < datetime.date.today():
        return jsonify({"status": "error", "message": "License expired"}), 403

    # --- Activation tracking
    hwids = record.get("activated_hwids", [])
    max_activations = record.get("max_activations", 2)

    if hwid not in hwids:
        # Auto-register this device if limit not exceeded
        if len(hwids) >= max_activations:
            return jsonify({
                "status": "error",
                "message": "Activation limit reached. Please deactivate another device first."
            }), 403

        hwids.append(hwid)
        record["activated_hwids"] = hwids
        db[license_key] = record
        save_db(db)

    # --- Build full response with all details
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


@app.route("/create_license", methods=["POST"])
def create_license():
    """Admin endpoint to create new license keys remotely."""
    import random, string

    # ✅ Security check — prevent public abuse
    secret = request.args.get("key")
    if secret != "Newo_Lomb_DTF_2025":  # 🔒 change this to something private
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    payload = request.get_json()
    customer = payload.get("customer")
    expiry = payload.get("expiry", "2026-12-31")
    max_activations = int(payload.get("max_activations", 1))
    product = payload.get("product", "Lombardi Print Studio Pro")
    version = payload.get("version", "1.0.0")

    # Validate customer name
    if not customer:
        return jsonify({"status": "error", "message": "Missing customer name"}), 400

    # ✅ Generate random license key (format: ABCD-EFGH-123)
    chars = string.ascii_uppercase + string.digits
    random_key = "".join(random.choices(chars, k=8))
    license_key = f"{random_key[:4]}-{random_key[4:]}-{random.randint(100,999)}"

    # Load DB and save new license
    db = load_db()
    db[license_key] = {
        "customer": customer,
        "expiry": expiry,
        "max_activations": max_activations,
        "activated_hwids": [],
        "product": product,
        "version": version
    }
    save_db(db)

    print(f"✅ Created new license for {customer}: {license_key}")

    return jsonify({
        "status": "ok",
        "message": "License created successfully",
        "license_key": license_key,
        "customer": customer,
        "expiry": expiry,
        "max_activations": max_activations
    })


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running", "message": "License Server is online"})


@app.route("/debug/licenses", methods=["GET"])
def debug_view_licenses():
    if not os.path.exists(LICENSE_DB):
        return jsonify({"error": f"{LICENSE_DB} not found"}), 404
    with open(LICENSE_DB, "r") as f:
        data = json.load(f)
    print(f"🧩 DEBUG — Reading from {os.path.abspath(LICENSE_DB)}")
    return jsonify(data)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
