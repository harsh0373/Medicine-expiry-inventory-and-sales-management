from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# Serve React build folder as static
app = Flask(__name__)
CORS(app)

# Update these values with your actual MySQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:password@localhost/med_app_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------------- MODELS ---------------------
class MedInfo(db.Model):
    _tablename_ = 'med_info'
    med_id = db.Column(db.Integer, primary_key=True)
    med_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(100), nullable=False)

class MedStock(db.Model):
    _tablename_ = 'med_stock'
    expiry_id = db.Column(db.Integer, primary_key=True)
    medid = db.Column(db.Integer, db.ForeignKey('med_info.med_id'), nullable=False)
    medname = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expirydate = db.Column(db.Date, nullable=False)
    buy_price_perunit = db.Column(db.Float, nullable=False)

from datetime import date
class MedSales(db.Model):
    _tablename_ = 'med_sales'
    saleid = db.Column(db.Integer, primary_key=True)
    expiryid = db.Column(db.Integer, db.ForeignKey('med_stock.expiry_id'), nullable=False)
    medname = db.Column(db.String(100), nullable=False)
    custname = db.Column(db.String(100), nullable=False)
    custcontact = db.Column(db.String(20), nullable=False)
    currdate = db.Column(db.Date, nullable=False, default=date.today)
    quantity = db.Column(db.Integer, nullable=False)
    sell_price_perunit = db.Column(db.Float, nullable=False)

# --------------------- API ROUTES ---------------------
@app.route("/api/medinfo", methods=["GET"])
def get_medinfo():
    meds = MedInfo.query.all()
    result = [{"med_id": m.med_id, "med_name": m.med_name, "brand": m.brand,
               "category": m.category, "type": m.type} for m in meds]
    return jsonify(result)

@app.route("/api/medinfo", methods=["POST"])
def add_medinfo():
    data = request.json
    new_med = MedInfo(
        med_name=data["med_name"],
        brand=data["brand"],
        category=data["category"],
        type=data["type"]
    )
    db.session.add(new_med)
    db.session.commit()
    return jsonify({"message": "Medicine info added!"}), 201

# (Baaki ke API routes aise hi rahenge, tumhare original code se)

# --------------------- Serve React Frontend ---------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    """
    Serve React app for any route not starting with /api
    """
    if path.startswith("api"):
        return jsonify({"error": "API route not found"}), 404
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

# --------------------- MAIN ---------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create tables if not exist
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
