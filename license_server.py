from flask import Flask, request, jsonify
import json, os, datetime

app = Flask(__name__)

LICENSE_DB = os.path.join(os.path.dirname(__file__), "licenses.json")

import random, string

def generate_license_key(prefix="DTF", suffix="XYZ"):
    """Generate professional-style license key (e.g., DTF-9QK2-X8WR-2TLP-XYZ)."""
    parts = ["".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
    return f"{prefix}-{'-'.join(parts)}-{suffix}"



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

@app.route("/deactivate", methods=["POST"])
def deactivate():
    """Remove a specific HWID from a license (free up activation slot)."""
    payload = request.get_json()
    license_key = payload.get("license_key")
    hwid = payload.get("hwid")

    if not license_key or not hwid:
        return jsonify({"status": "error", "message": "Missing license key or HWID"}), 400

    db = load_db()
    if license_key not in db:
        return jsonify({"status": "error", "message": "Invalid license key"}), 404

    record = db[license_key]
    hwids = record.get("activated_hwids", [])

    if hwid in hwids:
        hwids.remove(hwid)
        record["activated_hwids"] = hwids
        db[license_key] = record
        save_db(db)
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


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running", "message": "License Server is online"})


@app.route("/debug/licenses", methods=["GET"])
def debug_view_licenses():
    """Nicely formatted HTML view of the current license database (debug use only)."""
    import json, html
    
    if not os.path.exists(LICENSE_DB):
        return jsonify({"error": f"{LICENSE_DB} not found"}), 404

    with open(LICENSE_DB, "r") as f:
        data = json.load(f)

    # Create a readable HTML layout
    html_content = "<h2>📜 License Database (Debug View)</h2>"
    html_content += "<table border='1' cellpadding='6' style='border-collapse:collapse;font-family:Segoe UI, sans-serif;'>"
    html_content += "<tr><th>License Key</th><th>Customer</th><th>Expiry</th><th>Activations</th><th>Activated HWIDs</th><th>Product</th></tr>"

    for key, record in data.items():
        html_content += f"""
        <tr>
            <td><b>{html.escape(key)}</b></td>
            <td>{html.escape(record.get('customer', ''))}</td>
            <td>{html.escape(record.get('expiry', ''))}</td>
            <td>{record.get('max_activations', '')}</td>
            <td>{', '.join(record.get('activated_hwids', [])) or '-'}</td>
            <td>{html.escape(record.get('product', ''))}</td>
        </tr>
        """

    html_content += "</table>"

    return html_content

# ==========================================================
# 🟩 ADMIN ENDPOINT: Create New License
# ==========================================================
# ==========================================================
# 🟩 ADMIN ENDPOINT: Create New License
# ==========================================================
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

    import random, string
    license_key = generate_license_key()


    db = load_db()
    db[license_key] = {
        "customer": customer,
        "expiry": expiry,
        "max_activations": max_activations,
        "activated_hwids": [],
        "product": product
    }
    save_db(db)

    return jsonify({
        "status": "ok",
        "message": "License created successfully",
        "license_key": license_key
    })

@app.route("/delete_license", methods=["POST"])
def delete_license():
    """
    Deletes a license by key.
    Supports both JSON body and URL parameters.
    Example browser link:
      https://license-server-2-yy9u.onrender.com/delete_license?key=Newo_Lomb_DTF_2025&license_key=ABC123-XYZ
    Example JSON body (Postman):
      { "license_key": "ABC123-XYZ" }
    """

    from flask import request

    # Accept both JSON and query string
    data = request.get_json(silent=True) or {}
    license_key = data.get("license_key") or request.args.get("license_key")
    admin_key = request.args.get("key", "")

    # --- Verify admin access
    if admin_key != "Newo_Lomb_DTF_2025":
        return jsonify({"status": "error", "message": "❌ Unauthorized request"}), 403

    if not license_key:
        return jsonify({"status": "error", "message": "⚠️ Missing license_key"}), 400

    # --- Load database
    db = load_db()

    if license_key not in db:
        return jsonify({"status": "error", "message": f"License '{license_key}' not found"}), 404

    # --- Delete and save
    del db[license_key]
    save_db(db)

    print(f"🗑️ License deleted: {license_key}")

    return jsonify({
        "status": "ok",
        "message": f"✅ License '{license_key}' deleted successfully."
    }), 200



if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Use Render's dynamic port
    app.run(host="0.0.0.0", port=port)