from flask import Flask, request, jsonify
import json, os, datetime

app = Flask(__name__)
LICENSE_DB = "licenses.json"

def load_db():
    if not os.path.exists(LICENSE_DB):
        with open(LICENSE_DB, "w") as f:
            json.dump({}, f)
    with open(LICENSE_DB, "r") as f:
        return json.load(f)

def save_db(data):
    with open(LICENSE_DB, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/activate", methods=["POST"])
def activate():
    payload = request.get_json()
    license_key = payload.get("license_key")
    hwid = payload.get("hwid")

    db = load_db()
    if license_key not in db:
        return jsonify({"status": "error", "message": "Invalid license key"}), 400

    record = db[license_key]
    expiry = datetime.datetime.strptime(record["expiry"], "%Y-%m-%d").date()
    if expiry < datetime.date.today():
        return jsonify({"status": "error", "message": "License expired"}), 403

    hwids = record.get("activated_hwids", [])
    max_activations = record.get("max_activations", 2)

    if hwid not in hwids:
        if len(hwids) >= max_activations:
            return jsonify({"status": "error", "message": "Maximum activations reached"}), 403
        hwids.append(hwid)
        record["activated_hwids"] = hwids
        db[license_key] = record
        save_db(db)

    return jsonify({
        "status": "ok",
        "message": "License activated successfully",
        "expiry": record["expiry"],
        "remaining": max_activations - len(hwids)
    })

@app.route("/verify", methods=["POST"])
def verify():
    payload = request.get_json()
    license_key = payload.get("license_key")
    hwid = payload.get("hwid")

    db = load_db()
    record = db.get(license_key)
    if not record:
        return jsonify({"status": "error", "message": "Invalid license"}), 400

    if hwid not in record.get("activated_hwids", []):
        return jsonify({"status": "error", "message": "Not activated on this machine"}), 403

    expiry = datetime.datetime.strptime(record["expiry"], "%Y-%m-%d").date()
    if expiry < datetime.date.today():
        return jsonify({"status": "error", "message": "License expired"}), 403

    return jsonify({"status": "ok", "message": "License valid", "expiry": record["expiry"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
