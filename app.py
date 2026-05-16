import sqlite3
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'pharmacy_secret_key_2024'
DATABASE = 'pharmacy.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS role (
        role_id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name TEXT UNIQUE NOT NULL,
        description TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id INTEGER NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        FOREIGN KEY (role_id) REFERENCES role(role_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS medicine_category (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS medicine (
        medicine_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        generic_name TEXT,
        unit_price REAL NOT NULL,
        stock_qty INTEGER DEFAULT 0,
        reorder_level INTEGER DEFAULT 10,
        requires_prescription INTEGER DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES medicine_category(category_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS supplier (
        supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT NOT NULL,
        email TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS medicine_batch (
        batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        supplier_id INTEGER NOT NULL,
        batch_number TEXT NOT NULL,
        expiry_date DATE NOT NULL,
        quantity INTEGER NOT NULL,
        selling_price REAL NOT NULL,
        FOREIGN KEY (medicine_id) REFERENCES medicine(medicine_id),
        FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS customer (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sale (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        user_id INTEGER NOT NULL,
        sale_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_amount REAL NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
        FOREIGN KEY (user_id) REFERENCES user(user_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sale_item (
        sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        batch_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sale(sale_id),
        FOREIGN KEY (medicine_id) REFERENCES medicine(medicine_id),
        FOREIGN KEY (batch_id) REFERENCES medicine_batch(batch_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS purchase (
        purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        purchase_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_amount REAL NOT NULL,
        FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
        FOREIGN KEY (user_id) REFERENCES user(user_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS purchase_item (
        purchase_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_cost REAL NOT NULL,
        FOREIGN KEY (purchase_id) REFERENCES purchase(purchase_id),
        FOREIGN KEY (medicine_id) REFERENCES medicine(medicine_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS alert (
        alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        alert_type TEXT NOT NULL,
        message TEXT NOT NULL,
        is_resolved INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (medicine_id) REFERENCES medicine(medicine_id))''')
    
    # Insert default data
    c.execute("INSERT OR IGNORE INTO role (role_id, role_name) VALUES (1, 'Admin'), (2, 'Pharmacist')")
    admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO user (user_id, role_id, username, password_hash, full_name) VALUES (1, 1, 'admin', ?, 'Admin User')", (admin_hash,))
    pharma_hash = hashlib.sha256('pharma123'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO user (user_id, role_id, username, password_hash, full_name) VALUES (2, 2, 'pharmacist', ?, 'Staff Pharmacist')", (pharma_hash,))
    
    c.execute("INSERT OR IGNORE INTO medicine_category (category_id, category_name) VALUES (1, 'Antibiotics'), (2, 'Pain Relief'), (3, 'Vitamins')")
    c.execute("INSERT OR IGNORE INTO medicine (medicine_id, category_id, name, unit_price, stock_qty) VALUES (1, 1, 'Amoxicillin', 15.50, 100), (2, 2, 'Paracetamol', 5.00, 200), (3, 3, 'Vitamin C', 12.00, 150)")
    c.execute("INSERT OR IGNORE INTO supplier (supplier_id, company_name, phone) VALUES (1, 'PharmaDistributors', '1234567890')")
    c.execute("INSERT OR IGNORE INTO customer (customer_id, full_name, phone) VALUES (1, 'Walk-in Customer', 'N/A')")
    c.execute("INSERT OR IGNORE INTO medicine_batch (batch_id, medicine_id, supplier_id, batch_number, expiry_date, quantity, selling_price) VALUES (1, 1, 1, 'AMX001', '2025-12-31', 100, 15.50), (2, 2, 1, 'PAR001', '2025-10-31', 200, 5.00), (3, 3, 1, 'VIT001', '2025-08-31', 150, 12.00)")
    
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        db = get_db()
        user = db.execute('SELECT u.*, r.role_name FROM user u JOIN role r ON u.role_id = r.role_id WHERE u.username = ? AND u.password_hash = ?', (username, password)).fetchone()
        db.close()
        if user:
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['role_name'] = user['role_name']
            flash(f'Welcome {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    total_medicines = db.execute('SELECT COUNT(*) as c FROM medicine').fetchone()['c']
    low_stock = db.execute('SELECT COUNT(*) as c FROM medicine WHERE stock_qty <= reorder_level').fetchone()['c']
    expiring = db.execute('SELECT COUNT(*) as c FROM medicine_batch WHERE expiry_date <= date("now", "+30 days") AND quantity > 0').fetchone()['c']
    today_sales = db.execute('SELECT COALESCE(SUM(total_amount),0) as t FROM sale WHERE date(sale_date) = date("now")').fetchone()['t']
    recent_sales = db.execute('SELECT s.sale_id, s.sale_date, s.total_amount, c.full_name as customer FROM sale s LEFT JOIN customer c ON s.customer_id = c.customer_id ORDER BY s.sale_date DESC LIMIT 5').fetchall()
    db.close()
    return render_template('dashboard.html', total_medicines=total_medicines, low_stock=low_stock, expiring_soon=expiring, total_sales_today=today_sales, recent_sales=recent_sales)

@app.route('/medicines')
@login_required
def medicines():
    db = get_db()
    medicines = db.execute('SELECT m.*, c.category_name FROM medicine m JOIN medicine_category c ON m.category_id = c.category_id').fetchall()
    categories = db.execute('SELECT * FROM medicine_category').fetchall()
    db.close()
    return render_template('medicines.html', medicines=medicines, categories=categories)

@app.route('/add_medicine', methods=['POST'])
@login_required
def add_medicine():
    db = get_db()
    db.execute('INSERT INTO medicine (category_id, name, generic_name, unit_price, reorder_level, requires_prescription) VALUES (?, ?, ?, ?, ?, ?)',
               (request.form['category_id'], request.form['name'], request.form.get('generic_name',''), request.form['unit_price'], request.form['reorder_level'], 1 if request.form.get('requires_prescription') else 0))
    db.commit()
    db.close()
    flash('Medicine added', 'success')
    return redirect(url_for('medicines'))

@app.route('/suppliers')
@login_required
def suppliers():
    db = get_db()
    suppliers = db.execute('SELECT * FROM supplier').fetchall()
    db.close()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/add_supplier', methods=['POST'])
@login_required
def add_supplier():
    db = get_db()
    db.execute('INSERT INTO supplier (company_name, contact_person, phone, email) VALUES (?, ?, ?, ?)',
               (request.form['company_name'], request.form.get('contact_person',''), request.form['phone'], request.form.get('email','')))
    db.commit()
    db.close()
    flash('Supplier added', 'success')
    return redirect(url_for('suppliers'))

@app.route('/purchases', methods=['GET', 'POST'])
@login_required
def purchases():
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO purchase (supplier_id, user_id, total_amount) VALUES (?, ?, 0)', (request.form['supplier_id'], session['user_id']))
        purchase_id = cursor.lastrowid
        medicines = request.form.getlist('medicine_id[]')
        quantities = request.form.getlist('quantity[]')
        costs = request.form.getlist('unit_cost[]')
        sell_prices = request.form.getlist('selling_price[]')
        expiry_dates = request.form.getlist('expiry_date[]')
        total = 0
        for i in range(len(medicines)):
            qty = int(quantities[i])
            cost = float(costs[i])
            total += qty * cost
            cursor.execute('INSERT INTO purchase_item (purchase_id, medicine_id, quantity, unit_cost) VALUES (?, ?, ?, ?)', (purchase_id, medicines[i], qty, cost))
            cursor.execute('''INSERT INTO medicine_batch (medicine_id, supplier_id, batch_number, expiry_date, quantity, selling_price)
                              VALUES (?, ?, ?, ?, ?, ?)''',
                           (medicines[i], request.form['supplier_id'], f"BATCH-{medicines[i]}-{datetime.now().strftime('%Y%m%d%H%M%S')}", expiry_dates[i], qty, float(sell_prices[i])))
            cursor.execute('UPDATE medicine SET stock_qty = stock_qty + ? WHERE medicine_id = ?', (qty, medicines[i]))
        cursor.execute('UPDATE purchase SET total_amount = ? WHERE purchase_id = ?', (total, purchase_id))
        db.commit()
        db.close()
        flash('Purchase recorded', 'success')
        return redirect(url_for('purchases'))
    db = get_db()
    purchases = db.execute('SELECT p.*, s.company_name FROM purchase p JOIN supplier s ON p.supplier_id = s.supplier_id ORDER BY p.purchase_date DESC').fetchall()
    suppliers = db.execute('SELECT * FROM supplier').fetchall()
    medicines = db.execute('SELECT medicine_id, name FROM medicine').fetchall()
    db.close()
    return render_template('purchases.html', purchases=purchases, suppliers=suppliers, medicines=medicines)

@app.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO sale (customer_id, user_id, total_amount) VALUES (?, ?, 0)', (request.form.get('customer_id',1), session['user_id']))
        sale_id = cursor.lastrowid
        medicines = request.form.getlist('medicine_id[]')
        quantities = request.form.getlist('quantity[]')
        batch_ids = request.form.getlist('batch_id[]')
        prices = request.form.getlist('unit_price[]')
        total = 0
        for i in range(len(medicines)):
            qty = int(quantities[i])
            price = float(prices[i])
            total += qty * price
            cursor.execute('INSERT INTO sale_item (sale_id, medicine_id, batch_id, quantity, unit_price) VALUES (?, ?, ?, ?, ?)', (sale_id, medicines[i], batch_ids[i], qty, price))
            cursor.execute('UPDATE medicine_batch SET quantity = quantity - ? WHERE batch_id = ?', (qty, batch_ids[i]))
            cursor.execute('UPDATE medicine SET stock_qty = stock_qty - ? WHERE medicine_id = ?', (qty, medicines[i]))
        cursor.execute('UPDATE sale SET total_amount = ? WHERE sale_id = ?', (total, sale_id))
        db.commit()
        db.close()
        flash('Sale completed', 'success')
        return redirect(url_for('sales'))
    db = get_db()
    sales = db.execute('SELECT s.*, c.full_name as customer FROM sale s LEFT JOIN customer c ON s.customer_id = c.customer_id ORDER BY s.sale_date DESC LIMIT 20').fetchall()
    customers = db.execute('SELECT * FROM customer').fetchall()
    batches = db.execute('SELECT b.batch_id, b.medicine_id, m.name, b.quantity, b.selling_price FROM medicine_batch b JOIN medicine m ON b.medicine_id = m.medicine_id WHERE b.quantity > 0 AND b.expiry_date > date("now")').fetchall()
    db.close()
    return render_template('sales.html', sales=sales, customers=customers, batches=batches)

@app.route('/alerts')
@login_required
def alerts():
    db = get_db()
    alerts = db.execute('SELECT a.*, m.name as medicine_name FROM alert a JOIN medicine m ON a.medicine_id = m.medicine_id WHERE a.is_resolved = 0 ORDER BY a.created_at DESC').fetchall()
    db.close()
    return render_template('alerts.html', alerts=alerts)

@app.route('/resolve_alert/<int:alert_id>')
@login_required
def resolve_alert(alert_id):
    db = get_db()
    db.execute('UPDATE alert SET is_resolved = 1 WHERE alert_id = ?', (alert_id,))
    db.commit()
    db.close()
    flash('Alert resolved', 'success')
    return redirect(url_for('alerts'))

@app.route('/reports')
@login_required
def reports():
    db = get_db()
    top_medicines = db.execute('SELECT m.name, SUM(si.quantity) as sold FROM sale_item si JOIN medicine m ON si.medicine_id = m.medicine_id GROUP BY si.medicine_id ORDER BY sold DESC LIMIT 5').fetchall()
    expiring = db.execute('SELECT b.*, m.name as medicine_name FROM medicine_batch b JOIN medicine m ON b.medicine_id = m.medicine_id WHERE b.expiry_date <= date("now", "+30 days") AND b.quantity > 0').fetchall()
    db.close()
    return render_template('reports.html', top_medicines=top_medicines, expiring_batches=expiring)



if __name__ == '__main__':
    init_db()
    print("="*50)
    print("Smart Pharmacy Management System")
    print("="*50)
    print("Login Credentials:")
    print("Admin - username: admin | password: admin123")
    print("Staff - username: pharmacist | password: pharma123")
    print("="*50)
    print("Server running at: http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)


