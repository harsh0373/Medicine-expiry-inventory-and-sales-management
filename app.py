from flask import Flask ,request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app , resources={r"/*": {"origins": "https://med-app-frontend-five.vercel.app"}})

# Update these values with your actual MySQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:password@localhost/med_app_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class MedInfo(db.Model):
    __tablename__ = 'med_info'
    med_id = db.Column(db.Integer, primary_key=True)
    med_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(100), nullable=False)


@app.route("/api/medinfo", methods=["GET"])
def get_medinfo():
    meds = MedInfo.query.all()
    result = []
    for med in meds:
        result.append({
            "med_id": med.med_id,
            "med_name": med.med_name,
            "brand": med.brand,
            "category": med.category,
            "type": med.type
        })
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




class MedStock(db.Model):
    __tablename__ = 'med_stock'
    expiry_id = db.Column(db.Integer, primary_key=True)
    medid = db.Column(db.Integer, db.ForeignKey('med_info.med_id'), nullable=False)
    medname = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expirydate = db.Column(db.Date, nullable=False)
    buy_price_perunit = db.Column(db.Float, nullable=False)


@app.route("/api/medstock", methods=["GET"])
def get_medstock():
    meds = MedStock.query.all()
    result = []
    for med in meds:
        result.append({
            "medid": med.medid,
            "medname": med.medname,
            "quantity": med.quantity,
            "expirydate": med.expirydate.isoformat(),
            "buy_price_perunit": med.buy_price_perunit
        })
    return jsonify(result)

@app.route("/api/medstock", methods=["POST"])
def add_medstock():
    data = request.json
    
    medid = data["medid"]
    medname = data["medname"]
    quantity = data["quantity"]
    expirydate = data["expirydate"]
    buy_price_perunit = data["buy_price_perunit"]

    # Check agar record already exist karta hai same medid aur expirydate ke sath
    existing_stock = MedStock.query.filter_by(
        medid=medid, 
        expirydate=expirydate
    ).first()

    if existing_stock:
        # Agar record hai to uski quantity update kar do
        existing_stock.quantity += quantity
        db.session.commit()
        return jsonify({"message": "Quantity updated successfully!"}), 200
    else:
        # Agar nahi hai to naya record insert karo
        new_stock = MedStock(
            medid=medid,
            medname=medname,
            quantity=quantity,
            expirydate=expirydate,
            buy_price_perunit=buy_price_perunit
        )
        db.session.add(new_stock)
        db.session.commit()
        return jsonify({"message": "New stock added!"}),201
    
@app.route("/api/available_meds", methods=["GET"])
def get_available_meds():
    results = db.session.query(
        MedStock.medid,
        MedStock.medname,
        MedStock.quantity,
        MedInfo.brand,
        MedInfo.type
    ).join(MedInfo, MedStock.medid == MedInfo.med_id).all()
    
    meds_list = []
    for med in results:
        meds_list.append({
            "med_id": med.medid,
            "med_name": med.medname,
            "quantity": med.quantity,
            "brand": med.brand,
            "type": med.type
        })
    return jsonify(meds_list)


from datetime import date

class MedSales(db.Model):
    __tablename__ = 'med_sales'
    saleid = db.Column(db.Integer, primary_key=True)
    expiryid = db.Column(db.Integer, db.ForeignKey('med_stock.expiry_id'), nullable=False)
    medname = db.Column(db.String(100), nullable=False)
    custname = db.Column(db.String(100), nullable=False)
    custcontact = db.Column(db.String(20), nullable=False)
    currdate = db.Column(db.Date, nullable=False, default=date.today)
    quantity = db.Column(db.Integer, nullable=False)
    sell_price_perunit = db.Column(db.Float, nullable=False)




# Sales API endpoints
@app.route("/api/sales", methods=["POST"])
def create_sale():
    data = request.json
    
    # Validate required fields
    required_fields = ['medid', 'medname', 'custname', 'custcontact', 'quantity', 'sell_price_perunit']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    try:
        # Get the stock entry for this medicine
        stock_entry = MedStock.query.filter_by(medid=data['medid']).first()
        
        if not stock_entry:
            return jsonify({"error": "Medicine not found in stock"}), 404
        
        if stock_entry.quantity < data['quantity']:
            return jsonify({"error": f"Insufficient stock. Available: {stock_entry.quantity}"}), 400
        
        # Create sale record
        new_sale = MedSales(
            expiryid=stock_entry.expiry_id,
            medname=data['medname'],
            custname=data['custname'],
            custcontact=data['custcontact'],
            quantity=data['quantity'],
            sell_price_perunit=data['sell_price_perunit']
        )
        
        # Update stock quantity
        stock_entry.quantity -= data['quantity']
        
        db.session.add(new_sale)
        db.session.commit()
        
        return jsonify({
            "message": "Sale completed successfully!",
            "sale_id": new_sale.saleid,
            "total_amount": data['quantity'] * data['sell_price_perunit']
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/sales", methods=["GET"])
def get_sales():
    try:
        sales = MedSales.query.order_by(MedSales.currdate.desc()).all()
        result = []
        
        for sale in sales:
            result.append({
                "sale_id": sale.saleid,
                "medname": sale.medname,
                "custname": sale.custname,
                "custcontact": sale.custcontact,
                "quantity": sale.quantity,
                "sell_price_perunit": sale.sell_price_perunit,
                "total_amount": sale.quantity * sale.sell_price_perunit,
                "currdate": sale.currdate.isoformat()
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sales/today", methods=["GET"])
def get_today_sales():
    try:
        today = date.today()
        sales = MedSales.query.filter_by(currdate=today).all()
        
        total_amount = sum(sale.quantity * sale.sell_price_perunit for sale in sales)
        
        result = {
            "date": today.isoformat(),
            "total_sales": len(sales),
            "total_amount": total_amount,
            "sales": []
        }
        
        for sale in sales:
            result["sales"].append({
                "sale_id": sale.saleid,
                "medname": sale.medname,
                "custname": sale.custname,
                "quantity": sale.quantity,
                "sell_price_perunit": sale.sell_price_perunit,
                "total_amount": sale.quantity * sale.sell_price_perunit
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sales/bulk", methods=["POST"])
def create_bulk_sale():
    data = request.json
    
    if 'sales' not in data or 'custname' not in data or 'custcontact' not in data:
        return jsonify({"error": "Missing required fields: sales, custname, custcontact"}), 400
    
    try:
        total_amount = 0
        created_sales = []
        
        for sale_item in data['sales']:
            # Validate each sale item
            required_fields = ['medid', 'medname', 'quantity', 'sell_price_perunit']
            for field in required_fields:
                if field not in sale_item:
                    return jsonify({"error": f"Missing required field in sale item: {field}"}), 400
            
            # Get stock entry
            stock_entry = MedStock.query.filter_by(medid=sale_item['medid']).first()
            
            if not stock_entry:
                return jsonify({"error": f"Medicine {sale_item['medname']} not found in stock"}), 404
            
            if stock_entry.quantity < sale_item['quantity']:
                return jsonify({"error": f"Insufficient stock for {sale_item['medname']}. Available: {stock_entry.quantity}"}), 400
            
            # Create sale record
            new_sale = MedSales(
                expiryid=stock_entry.expiry_id,
                medname=sale_item['medname'],
                custname=data['custname'],
                custcontact=data['custcontact'],
                quantity=sale_item['quantity'],
                sell_price_perunit=sale_item['sell_price_perunit']
            )
            
            # Update stock quantity
            stock_entry.quantity -= sale_item['quantity']
            
            db.session.add(new_sale)
            created_sales.append(new_sale)
            
            total_amount += sale_item['quantity'] * sale_item['sell_price_perunit']
        
        db.session.commit()
        
        return jsonify({
            "message": "Bulk sale completed successfully!",
            "total_sales": len(created_sales),
            "total_amount": total_amount,
            "sale_ids": [sale.saleid for sale in created_sales]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Expiry tracking API endpoint
@app.route("/api/expiry_tracker", methods=["GET"])
def get_expiry_tracker():
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Get all stock with medicine info
        stock_with_info = db.session.query(
            MedStock.expiry_id,
            MedStock.medid,
            MedStock.medname,
            MedStock.quantity,
            MedStock.expirydate,
            MedInfo.brand,
            MedInfo.type
        ).join(MedInfo, MedStock.medid == MedInfo.med_id).all()
        
        # Calculate date 30 days ago for sales analysis
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        today = datetime.now().date()
        
        result = []
        
        for stock in stock_with_info:
            # Calculate remaining days until expiry
            remaining_days = (stock.expirydate - today).days
            
            # Get sales data for this medicine in last 30 days
            sales_data = db.session.query(
                func.sum(MedSales.quantity).label('total_sold')
            ).filter(
                MedSales.expiryid == stock.expiry_id,
                MedSales.currdate >= thirty_days_ago,
                MedSales.currdate <= today
            ).first()
            
            total_sold = sales_data.total_sold if sales_data.total_sold else 0
            
            # Calculate average daily sales (total sold in 30 days / 30)
            avg_daily_sales = total_sold / 30 if total_sold > 0 else 0
            
            # Calculate days to sell current stock
            days_to_sell = stock.quantity / avg_daily_sales if avg_daily_sales > 0 else float('inf')
            
            # Calculate tracking result
            tracking_result = remaining_days - days_to_sell
            
            # Determine status
            if remaining_days < 0:
                status = "Expired"
                status_color = "#dc3545"
                status_icon = "❌"
            elif avg_daily_sales == 0:
                status = "No Sales Data"
                status_color = "#6c757d"
                status_icon = "📊"
            elif tracking_result > 0:
                status = f"Safe ({int(tracking_result)} days buffer)"
                status_color = "#28a745"
                status_icon = "✅"
            else:
                days_over = abs(int(tracking_result))
                status = f"Risk: Will expire {days_over} days before sold"
                status_color = "#dc3545"
                status_icon = "⚠️"
            
            result.append({
                "expiry_id": stock.expiry_id,
                "medid": stock.medid,
                "medname": stock.medname,
                "brand": stock.brand,
                "type": stock.type,
                "quantity": stock.quantity,
                "expirydate": stock.expirydate.isoformat(),
                "remaining_days": remaining_days,
                "total_sold_30days": total_sold,
                "avg_daily_sales": round(avg_daily_sales, 2),
                "days_to_sell_current_stock": round(days_to_sell, 2) if days_to_sell != float('inf') else None,
                "tracking_result": round(tracking_result, 2) if tracking_result != float('inf') else None,
                "status": status,
                "status_color": status_color,
                "status_icon": status_icon
            })
        
        # Sort by tracking result (most risky first)
        result.sort(key=lambda x: x['tracking_result'] if x['tracking_result'] is not None else float('-inf'))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "Flask app is running!"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # This creates the table if it doesn't exist
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
