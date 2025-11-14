from flask import Flask, request, jsonify
import json, os, datetime

app = Flask(__name__)

LICENSE_DB = "licenses.json"


# === Utility Functions ===
def load_db():
    if not os.path.exists(LICENSE_DB):
        with open(LICENSE_DB, "w") as f:
            json.dump({}, f)
    with open(LICENSE_DB, "r") as f:
        return json.load(f)


def save_db(data):
    with open(LICENSE_DB, "w") as f:
        json.dump(data, f, indent=4)


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
        "product": record.get("product", "Unknown Product"),
        "expiry": record["expiry"],
        "activated_hwids": record.get("activated_hwids", []),
        "max_activations": record.get("max_activations", 2),
        "activations_used": len(record.get("activated_hwids", []))
    })


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running", "message": "License Server is online"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
