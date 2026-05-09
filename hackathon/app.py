import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

app = Flask(__name__)

# CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///apples.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'kashmir_apple_secret'

db = SQLAlchemy(app)

# 1. DATABASE MODELS
class AppleLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variety = db.Column(db.String(50), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    box_count = db.Column(db.Integer, nullable=False)
    min_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Open')
    
    grower_name = db.Column(db.String(50))
    grower_phone = db.Column(db.String(15))
    locked_bid_id = db.Column(db.Integer, nullable=True)
    
    bids = db.relationship('Bid', backref='lot', lazy=True)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    bidder_name = db.Column(db.String(50), nullable=False)
    trader_phone = db.Column(db.String(15))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    lot_id = db.Column(db.Integer, db.ForeignKey('apple_lot.id'), nullable=False)

# 2. ROUTES
@app.route('/')
def home():
    return render_template('listing_form.html')

@app.route('/list-apples', methods=['POST'])
def list_apples():
    try:
        variety = request.form.get('variety', 'Generic')
        grade = request.form.get('grade', 'Standard')
        boxes = int(request.form.get('boxes', 0))
        price = float(request.form.get('price', 0.0))
        g_name = request.form.get('grower_name')
        g_phone = request.form.get('grower_phone')

        new_lot = AppleLot()
        new_lot.variety = variety
        new_lot.grade = grade
        new_lot.box_count = boxes
        new_lot.min_price = price
        new_lot.grower_name = g_name
        new_lot.grower_phone = g_phone

        db.session.add(new_lot)
        db.session.commit()
        flash("Lot posted successfully!", "success")
        return redirect(url_for('grower_dashboard'))
    except Exception as e:
        db.session.rollback()
        return f"Error: {e}"

@app.route('/grower/dashboard')
@app.route('/grower/my-bids')
def grower_dashboard():
    all_lots = AppleLot.query.all()
    return render_template('grower_bids.html', lots=all_lots)

@app.route('/trader/dashboard')
def trader_dashboard():
    selected_variety = request.args.get('variety', 'All')
    query = AppleLot.query
    if selected_variety != 'All':
        query = query.filter_by(variety=selected_variety)
    open_lots = query.all()

    varieties = [row[0] for row in db.session.query(AppleLot.variety).distinct().all() if row[0]]
    varieties.sort()

    return render_template(
        'trader_view.html',
        lots=open_lots,
        varieties=varieties,
        selected_variety=selected_variety
    )

@app.route('/bid/<int:lot_id>', methods=['POST'])
def place_bid(lot_id):
    try:
        bid_val = float(request.form.get('bid_amount', 0))
        bidder = request.form.get('trader_name')
        t_phone = request.form.get('trader_phone')
        
        lot = AppleLot.query.get(lot_id)
        if lot:
            if lot.status == "Locked":
                flash("Deal already locked!", "danger")
                return redirect(url_for('trader_dashboard'))
            if bid_val < lot.min_price:
                flash(f"Bid too low! Min: ₹{lot.min_price}", "danger")
                return redirect(url_for('trader_dashboard'))

            new_bid = Bid()
            new_bid.amount = bid_val
            new_bid.bidder_name = bidder
            new_bid.trader_phone = t_phone
            new_bid.lot_id = lot.id
            lot.status = "Bidded"
            db.session.add(new_bid)
            db.session.commit()
            flash(f"Bid of ₹{bid_val} placed!", "success")
        return redirect(url_for('trader_dashboard'))
    except Exception as e:
        db.session.rollback()
        return f"Error: {e}"

@app.route('/lock-deal/<int:bid_id>', methods=['POST'])
def lock_deal(bid_id):
    try:
        bid = Bid.query.get(bid_id)
        if bid:
            lot = bid.lot
            lot.status = "Locked"
            lot.locked_bid_id = bid.id
            db.session.commit()
            flash(f"Deal Locked with {bid.bidder_name}!", "success")
        return redirect(url_for('grower_dashboard'))
    except Exception as e:
        db.session.rollback()
        return f"Error: {e}"
# NEW ROUTE: Locking the Deal
@app.route('/lock-bid/<int:bid_id>', methods=['POST'])
def lock_bid(bid_id):
    try:
        bid = Bid.query.get(bid_id)
        if bid:
            lot = bid.lot
            lot.locked_bid_id = bid.id
            lot.status = "Locked"
            db.session.commit()
            flash(f"Deal Locked with {bid.bidder_name}! Contact details exchanged.", "success")
        return redirect(url_for('grower_dashboard'))
    except Exception as e:
        db.session.rollback()
        return f"Error: {e}"
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Render uses an environment variable called PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)