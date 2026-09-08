import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'campkart-dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE, 'instance', 'campkart.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(BASE, 'instance'), exist_ok=True)

db = SQLAlchemy(app)

CATEGORIES = ['Books', 'Calculators', 'Lab Items', 'Drawing Instruments', 'Stationery', 'Electronics', 'Hostel Items', 'Sports Equipment', 'Project Components', 'Uniforms']
ALLOWED = {'png', 'jpg', 'jpeg', 'webp'}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    student_id = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(30), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    condition = db.Column(db.String(40), nullable=False)
    image = db.Column(db.String(255))
    sale_price = db.Column(db.Float)
    rent_day = db.Column(db.Float)
    rent_week = db.Column(db.Float)
    rent_month = db.Column(db.Float)
    mode = db.Column(db.String(20), default='sell')
    available = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller = db.relationship('User', backref='listings')

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    duration = db.Column(db.String(30))
    amount = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    listing = db.relationship('Listing')
    buyer = db.relationship('User')

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(30), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    listing = db.relationship('Listing')
    reporter = db.relationship('User')

def current_user():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None

@app.context_processor
def inject_globals():
    return {'current_user': current_user(), 'categories': CATEGORIES}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash('Please log in first.', 'warning')
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or not u.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED

@app.route('/')
def home():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    mode = request.args.get('mode', '')
    query = Listing.query.filter_by(status='active', available=True)
    if q:
        query = query.filter(db.or_(Listing.name.ilike(f'%{q}%'), Listing.description.ilike(f'%{q}%')))
    if category in CATEGORIES:
        query = query.filter_by(category=category)
    if mode in ('sell', 'rent'):
        query = query.filter_by(mode=mode)
    listings = query.order_by(Listing.created_at.desc()).all()
    return render_template('home.html', listings=listings, q=q, category=category, mode=mode)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        domain = os.getenv('COLLEGE_DOMAIN', '').strip().lower()
        if domain and not email.endswith('@' + domain):
            flash('Use your official college email address.', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html')
        u = User(name=request.form['name'].strip(), email=email,
                 password_hash=generate_password_hash(request.form['password']),
                 student_id=request.form['student_id'].strip(), department=request.form['department'].strip(),
                 semester=request.form['semester'].strip(), phone=request.form['phone'].strip())
        db.session.add(u); db.session.commit()
        flash('Account created. Admin verification is required before listing items.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if u and check_password_hash(u.password_hash, request.form['password']):
            session['user_id'] = u.id
            return redirect(request.args.get('next') or url_for('home'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('home'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    item = db.get_or_404(Listing, listing_id)
    if item.status != 'active': abort(404)
    return render_template('listing.html', item=item)

@app.route('/sell', methods=['GET','POST'])
@login_required
def sell():
    u = current_user()
    if not u.verified:
        flash('Your account must be verified before listing an item.', 'warning')
        return redirect(url_for('profile'))
    if request.method == 'POST':
        image_name = None
        f = request.files.get('image')
        if f and f.filename:
            if not allowed_file(f.filename):
                flash('Image must be PNG, JPG, JPEG or WEBP.', 'danger'); return render_template('sell.html')
            image_name = secure_filename(f'{u.id}_{datetime.utcnow().timestamp()}_{f.filename}')
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))
        mode = request.form['mode']
        item = Listing(seller_id=u.id, name=request.form['name'].strip(), description=request.form['description'].strip(),
                       category=request.form['category'], condition=request.form['condition'], image=image_name,
                       sale_price=float(request.form['sale_price']) if request.form.get('sale_price') else None,
                       rent_day=float(request.form['rent_day']) if request.form.get('rent_day') else None,
                       rent_week=float(request.form['rent_week']) if request.form.get('rent_week') else None,
                       rent_month=float(request.form['rent_month']) if request.form.get('rent_month') else None,
                       mode=mode)
        db.session.add(item); db.session.commit()
        flash('Listing published successfully.', 'success'); return redirect(url_for('listing_detail', listing_id=item.id))
    return render_template('sell.html')

@app.route('/reserve/<int:listing_id>', methods=['POST'])
@login_required
def reserve(listing_id):
    item = db.get_or_404(Listing, listing_id); u = current_user()
    if not u.verified:
        flash('Only verified students can make reservations.', 'warning'); return redirect(url_for('listing_detail', listing_id=listing_id))
    if item.seller_id == u.id:
        flash('You cannot reserve your own listing.', 'warning'); return redirect(url_for('listing_detail', listing_id=listing_id))
    tx = request.form.get('transaction_type', item.mode)
    duration = request.form.get('duration') or None
    amount = item.sale_price if tx == 'sell' else {'day': item.rent_day, 'week': item.rent_week, 'month': item.rent_month}.get(duration)
    if amount is None:
        flash('That option is not available.', 'danger'); return redirect(url_for('listing_detail', listing_id=listing_id))
    commission = round(amount * 0.10, 2)
    db.session.add(Reservation(listing_id=item.id, buyer_id=u.id, transaction_type=tx, duration=duration, amount=amount, commission=commission))
    db.session.commit(); flash('Reservation request sent to the seller.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/report/<int:listing_id>', methods=['POST'])
@login_required
def report(listing_id):
    item = db.get_or_404(Listing, listing_id)
    db.session.add(Report(listing_id=item.id, reporter_id=current_user().id, reason=request.form['reason'].strip()))
    db.session.commit(); flash('Report submitted for review.', 'success'); return redirect(url_for('listing_detail', listing_id=listing_id))

@app.route('/dashboard')
@login_required
def dashboard():
    u = current_user()
    mine = Listing.query.filter_by(seller_id=u.id).order_by(Listing.created_at.desc()).all()
    reservations = Reservation.query.filter_by(buyer_id=u.id).order_by(Reservation.created_at.desc()).all()
    return render_template('dashboard.html', mine=mine, reservations=reservations)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user())

@app.route('/admin')
@admin_required
def admin():
    users = User.query.order_by(User.created_at.desc()).all()
    reports = Report.query.order_by(Report.created_at.desc()).all()
    listings = Listing.query.order_by(Listing.created_at.desc()).all()
    reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
    return render_template('admin.html', users=users, reports=reports, listings=listings, reservations=reservations)

@app.route('/admin/verify/<int:user_id>', methods=['POST'])
@admin_required
def verify(user_id):
    u = db.get_or_404(User, user_id); u.verified = True; db.session.commit(); flash('Student verified.', 'success'); return redirect(url_for('admin'))

@app.route('/admin/listing/<int:listing_id>/hide', methods=['POST'])
@admin_required
def hide_listing(listing_id):
    item = db.get_or_404(Listing, listing_id); item.status='hidden'; db.session.commit(); flash('Listing hidden.', 'success'); return redirect(url_for('admin'))

@app.route('/admin/report/<int:report_id>/close', methods=['POST'])
@admin_required
def close_report(report_id):
    r = db.get_or_404(Report, report_id); r.status='closed'; db.session.commit(); return redirect(url_for('admin'))

def seed():
    db.create_all()
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@campkart.local')
    admin_pw = os.getenv('ADMIN_PASSWORD', 'ChangeMe123!')
    if not User.query.filter_by(email=admin_email).first():
        db.session.add(User(name='CAMPKART Admin', email=admin_email, password_hash=generate_password_hash(admin_pw), student_id='ADMIN', department='Administration', semester='N/A', phone='0000000000', verified=True, is_admin=True))
        db.session.commit()

if __name__ == '__main__':
    with app.app_context(): seed()
    app.run(debug=True)
