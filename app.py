from flask import Flask, render_template_string, request, jsonify, session
import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Enterprise State Management
gateway_state = {
    "admin_user": "",
    "admin_pass": "",
    "gmail_user": "",
    "gmail_pass": "",
    "upi_id": "sunny8127@fam",
    "api_key": "fp_live_" + os.urandom(12).hex(),
    "is_installed": False,
    "is_setup_done": False,
    "total_revenue": 0.0,
    "transactions": []
}

# ==========================================
# HTML TEMPLATES (Embedded for Single File)
# ==========================================

BASE_STYLE = """
<style>
    :root {
        --primary-blue: #0284c7;
        --secondary-blue: #0369a1;
        --bg-glass: rgba(255, 255, 255, 0.85);
        --border-glass: rgba(255, 255, 255, 0.6);
        --text-main: #0f172a;
        --text-muted: #64748b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    body {
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 50%, #7dd3fc 100%);
        min-height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
        color: var(--text-main);
        padding: 20px;
    }
    .glass-container {
        background: var(--bg-glass);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-glass);
        border-radius: 24px;
        box-shadow: 0 20px 40px rgba(2, 132, 199, 0.15);
        width: 100%;
        max-width: 650px;
        padding: 35px;
    }
    .wide-container { max-width: 900px; }
    .gateway-header { text-align: center; margin-bottom: 25px; }
    .logo-icon {
        font-size: 32px;
        color: var(--primary-blue);
        background: rgba(2, 132, 199, 0.1);
        width: 64px; height: 64px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 50%;
        margin: 0 auto 12px auto;
    }
    h1 { font-size: 24px; font-weight: 700; color: var(--text-main); }
    p { color: var(--text-muted); font-size: 14px; margin-top: 4px; }
    .panel {
        background: rgba(255, 255, 255, 0.6);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
    }
    .input-group { margin-bottom: 15px; text-align: left; }
    label { display: block; font-size: 13px; font-weight: 600; color: var(--text-main); margin-bottom: 6px; }
    input {
        width: 100%;
        padding: 12px 16px;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        font-size: 14px;
        color: var(--text-main);
        outline: none;
        transition: all 0.2s;
    }
    input:focus { border-color: var(--primary-blue); box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15); }
    .btn-primary {
        width: 100%;
        padding: 12px;
        background: var(--primary-blue);
        color: #ffffff;
        border: none;
        border-radius: 10px;
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s;
    }
    .btn-primary:hover { background: var(--secondary-blue); }
    .btn-secondary {
        background: #e2e8f0;
        color: var(--text-main);
        border: none;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        font-size: 13px;
    }
    .api-row { display: flex; gap: 8px; }
    .stats-card {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: #ffffff;
        padding: 20px;
        border-radius: 14px;
        margin-bottom: 20px;
    }
    .stats-card h3 { font-size: 28px; margin-top: 5px; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 10px; text-align: left; font-size: 13px; border-bottom: 1px solid #e2e8f0; }
    th { color: var(--text-muted); font-weight: 600; }
    .badge-success { background: #dcfce7; color: #15803d; padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 11px; }
    .message { margin-top: 12px; font-size: 13px; font-weight: 600; text-align: center; }
</style>
"""

SETUP_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>Gateway Setup</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {{ base_style | safe }}
</head>
<body>
    <div class="glass-container">
        <div class="gateway-header">
            <div class="logo-icon"><i class="fa-solid fa-shield-halved"></i></div>
            <h1 id="title-text">Admin Setup</h1>
            <p id="sub-text">Configure your private credentials</p>
        </div>
        <div class="panel">
            <!-- Step 1: Register -->
            <div id="step-register" style="display: {% if step == 'register' %}block{% else %}none{% endif %};">
                <div class="input-group"><label>Admin Username</label><input type="text" id="reg-user" placeholder="Choose username"></div>
                <div class="input-group"><label>Admin Password</label><input type="password" id="reg-pass" placeholder="Choose password"></div>
                <button class="btn-primary" onclick="registerAdmin()">Create Admin Account</button>
            </div>
            <!-- Step 2: Login -->
            <div id="step-login" style="display: {% if step == 'login' %}block{% else %}none{% endif %};">
                <div class="input-group"><label>Admin Username</label><input type="text" id="log-user" placeholder="Enter username"></div>
                <div class="input-group"><label>Admin Password</label><input type="password" id="log-pass" placeholder="Enter password"></div>
                <button class="btn-primary" onclick="loginAdmin()">Login to Gateway</button>
            </div>
            <!-- Step 3: Gateway Config -->
            <div id="step-config" style="display: {% if step == 'gateway_config' %}block{% else %}none{% endif %};">
                <div class="input-group"><label>Gmail Address</label><input type="email" id="g-user" placeholder="your-email@gmail.com"></div>
                <div class="input-group"><label>Gmail App Password (16 digits)</label><input type="password" id="g-pass" placeholder="abcd efgh ijkl mnop"></div>
                <div class="input-group"><label>Target UPI ID</label><input type="text" id="g-upi" value="sunny8127@fam"></div>
                <button class="btn-primary" onclick="setupGateway()">Connect & Launch Gateway</button>
            </div>
            <div id="msg" class="message"></div>
        </div>
    </div>
    <script>
        async function registerAdmin() {
            let res = await fetch('/api/register-admin', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:document.getElementById('reg-user').value, password:document.getElementById('reg-pass').value})});
            let d = await res.json();
            if(d.status==='success') location.reload(); else alert(d.message);
        }
        async function loginAdmin() {
            let res = await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:document.getElementById('log-user').value, password:document.getElementById('log-pass').value})});
            let d = await res.json();
            if(d.status==='success') location.reload(); else alert(d.message);
        }
        async function setupGateway() {
            let res = await fetch('/api/setup-gateway', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({gmail_user:document.getElementById('g-user').value, gmail_pass:document.getElementById('g-pass').value, upi_id:document.getElementById('g-upi').value})});
            let d = await res.json();
            if(d.status==='success') location.reload(); else alert(d.message);
        }
    </script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>FamPay Enterprise Dashboard</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {{ base_style | safe }}
</head>
<body>
    <div class="glass-container wide-container">
        <div class="gateway-header" style="display:flex; justify-content:space-between; align-items:center;">
            <div style="text-align:left;">
                <h1>FamPay Enterprise Gateway</h1>
                <p>Live URL: <strong style="color:var(--primary-blue);">{{ live_url }}</strong></p>
            </div>
            <button onclick="logout()" class="btn-secondary" style="background:#fee2e2; color:#dc2626;"><i class="fa-solid fa-power-off"></i> Logout</button>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
            <div class="panel">
                <h3 style="margin-bottom:15px;"><i class="fa-solid fa-code"></i> Developer API & Checkout</h3>
                <div class="input-group">
                    <label>Public Checkout Page URL</label>
                    <div class="api-row"><input type="text" readonly value="{{ live_url }}pay"><a href="{{ live_url }}pay" target="_blank" class="btn-secondary" style="text-decoration:none; display:flex; align-items:center;">Open</a></div>
                </div>
                <div class="input-group">
                    <label>API Endpoint</label>
                    <input type="text" readonly value="{{ live_url }}api/v1/verify-payment">
                </div>
                <div class="input-group">
                    <label>Secret API Key</label>
                    <div class="api-row">
                        <input type="text" readonly value="{{ api_key }}" id="api-key-val">
                        <button onclick="genKey()" class="btn-secondary">New Key</button>
                    </div>
                </div>
            </div>

            <div class="panel">
                <div class="stats-card">
                    <span>Total Collected Revenue</span>
                    <h3>₹ {{ total_revenue }}</h3>
                </div>
                <h3 style="margin-bottom:10px; font-size:15px;"><i class="fa-solid fa-clock-rotate-left"></i> Verified Transactions</h3>
                <div style="max-height:180px; overflow-y:auto;">
                    {% if transactions %}
                    <table>
                        <tr><th>Tx ID</th><th>Amount</th><th>Status</th><th>Time</th></tr>
                        {% for tx in transactions %}
                        <tr>
                            <td><code>{{ tx.tx_id }}</code></td>
                            <td>₹{{ tx.amount }}</td>
                            <td><span class="badge-success">{{ tx.status }}</span></td>
                            <td><small>{{ tx.time }}</small></td>
                        </tr>
                        {% endfor %}
                    </table>
                    {% else %}
                    <p style="color:var(--text-muted); font-size:13px; text-align:center; padding:20px;">No verified transactions yet.</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    <script>
        async function genKey() {
            let res = await fetch('/api/generate-key', {method:'POST'});
            let d = await res.json();
            if(d.status==='success') document.getElementById('api-key-val').value = d.api_key;
        }
        async function logout() {
            await fetch('/api/logout', {method:'POST'});
            location.reload();
        }
    </script>
</body>
</html>
"""

CHECKOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>Instant UPI Checkout</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {{ base_style | safe }}
    <style>
        .quick-amounts { display:grid; grid-template-columns: repeat(3, 1fr); gap:8px; margin-bottom:15px; }
        .amt-btn { background: rgba(2, 132, 199, 0.08); border: 1px solid rgba(2, 132, 199, 0.2); color: var(--primary-blue); padding:10px; border-radius:10px; font-weight:600; cursor:pointer; }
        .amt-btn:hover { background: var(--primary-blue); color:#fff; }
        .qr-box { text-align:center; background:#fff; padding:20px; border-radius:16px; border:1px solid #e2e8f0; margin-top:15px; display:none; }
    </style>
</head>
<body>
    <div class="glass-container">
        <div class="gateway-header">
            <div class="logo-icon"><i class="fa-solid fa-qrcode"></i></div>
            <h1>Instant UPI Checkout</h1>
            <p>Scan & Pay via FamPay / UPI App</p>
        </div>
        <div class="panel">
            <div class="input-group">
                <label><i class="fa-solid fa-indian-rupee-sign"></i> Enter Amount</label>
                <input type="number" id="amt" value="100" min="1">
            </div>
            <div class="quick-amounts">
                <button class="amt-btn" onclick="setAmt(50)">₹50</button>
                <button class="amt-btn" onclick="setAmt(100)">₹100</button>
                <button class="amt-btn" onclick="setAmt(500)">₹500</button>
                <button class="amt-btn" onclick="setAmt(1000)">₹1000</button>
                <button class="amt-btn" onclick="setAmt(2000)">₹2000</button>
                <button class="amt-btn" onclick="setAmt(5000)">₹5000</button>
            </div>
            <button class="btn-primary" onclick="genQR()"><i class="fa-solid fa-qrcode"></i> Generate QR Code</button>

            <div id="qr-container" class="qr-box">
                <p style="margin-bottom:10px; font-weight:600;">Scan with UPI App</p>
                <img id="qr-img" src="" style="width:180px; height:180px; margin-bottom:10px;" alt="QR">
                <p style="font-size:13px; margin-bottom:10px;">UPI ID: <strong>{{ upi_id }}</strong></p>
                <button id="verify-btn" class="btn-primary" style="background:#10b981;" onclick="verifyPayment()"><i class="fa-solid fa-rotate"></i> Check Payment Status</button>
            </div>
            <div id="status-msg" class="message"></div>
        </div>
    </div>
    <script>
        const upiId = "{{ upi_id }}";
        const apiKey = "{{ api_key }}";
        function setAmt(v) { document.getElementById('amt').value = v; }
        function genQR() {
            let a = document.getElementById('amt').value;
            if(!a || a <= 0) { alert('Enter valid amount'); return; }
            let uri = `upi://pay?pa=${upiId}&pn=Merchant&am=${a}&cu=INR`;
            document.getElementById('qr-img').src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=` + encodeURIComponent(uri);
            document.getElementById('qr-container').style.display = 'block';
        }
        async function verifyPayment() {
            let a = document.getElementById('amt').value;
            let btn = document.getElementById('verify-btn');
            let msg = document.getElementById('status-msg');
            btn.innerHTML = 'Verifying... <i class="fa-solid fa-spinner fa-spin"></i>';
            
            let res = await fetch('/api/v1/verify-payment', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({api_key: apiKey, amount: parseFloat(a)})
            });
            let d = await res.json();
            if(d.status === 'approved') {
                msg.style.color = '#15803d';
                msg.textContent = 'Approved! Payment verified successfully.';
                btn.innerHTML = 'Verified <i class="fa-solid fa-check"></i>';
            } else {
                msg.style.color = '#d97706';
                msg.textContent = 'Pending... Complete payment in your UPI app.';
                btn.innerHTML = 'Check Payment Status';
            }
        }
    </script>
</body>
</html>
"""

# ==========================================
# FLASK BACKEND ROUTES
# ==========================================

@app.route('/')
def index():
    if not gateway_state["is_installed"]:
        return render_template_string(SETUP_TEMPLATE, base_style=BASE_STYLE, step="register")
    if not session.get("logged_in"):
        return render_template_string(SETUP_TEMPLATE, base_style=BASE_STYLE, step="login")
    if not gateway_state["is_setup_done"]:
        return render_template_string(SETUP_TEMPLATE, base_style=BASE_STYLE, step="gateway_config")
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        base_style=BASE_STYLE,
        live_url=request.host_url,
        upi_id=gateway_state["upi_id"],
        total_revenue=gateway_state["total_revenue"],
        transactions=gateway_state["transactions"],
        api_key=gateway_state["api_key"]
    )

@app.route('/pay')
def checkout_page():
    return render_template_string(
        CHECKOUT_TEMPLATE,
        base_style=BASE_STYLE,
        upi_id=gateway_state["upi_id"],
        api_key=gateway_state["api_key"]
    )

@app.route('/api/register-admin', methods=['POST'])
def register_admin():
    d = request.json
    if not d.get('username') or not d.get('password'):
        return jsonify({"status": "error", "message": "Required fields missing."})
    gateway_state["admin_user"] = d.get('username')
    gateway_state["admin_pass"] = d.get('password')
    gateway_state["is_installed"] = True
    session["logged_in"] = True
    return jsonify({"status": "success"})

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    if d.get('username') == gateway_state["admin_user"] and d.get('password') == gateway_state["admin_pass"]:
        session["logged_in"] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid credentials."})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop("logged_in", None)
    return jsonify({"status": "success"})

@app.route('/api/setup-gateway', methods=['POST'])
def setup_gateway():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "Unauthorized."})
    d = request.json
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(d.get('gmail_user'), d.get('gmail_pass'))
        mail.logout()
        
        gateway_state["gmail_user"] = d.get('gmail_user')
        gateway_state["gmail_pass"] = d.get('gmail_pass')
        gateway_state["upi_id"] = d.get('upi_id', 'sunny8127@fam')
        gateway_state["is_setup_done"] = True
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gmail Auth Error: {str(e)}"})

@app.route('/api/generate-key', methods=['POST'])
def generate_key():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "Unauthorized."})
    gateway_state["api_key"] = "fp_live_" + os.urandom(12).hex()
    return jsonify({"status": "success", "api_key": gateway_state["api_key"]})

@app.route('/api/v1/verify-payment', methods=['POST'])
def external_verify_payment():
    d = request.json
    if not d.get('api_key') or d.get('api_key') != gateway_state["api_key"]:
        return jsonify({"status": "rejected", "message": "Invalid API key."}), 401
    
    if not gateway_state["is_setup_done"]:
        return jsonify({"status": "rejected", "message": "Gateway not configured."}), 400
        
    expected_amount = float(d.get('amount', 0))
    tx_id = 'FP_TXN_' + os.urandom(3).hex().upper()
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gateway_state["gmail_user"], gateway_state["gmail_pass"])
        mail.select("inbox")
        
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            status, messages = mail.search(None, 'ALL')
            
        latest_emails = messages[0].split()[-10:]
        payment_verified = False
        matched_details = ""

        for email_id in reversed(latest_emails):
            res, msg_data = mail.fetch(email_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                        
                    if str(expected_amount) in body or gateway_state["upi_id"].lower() in body.lower():
                        payment_verified = True
                        matched_details = f"Email: {subject}"
                        break
            if payment_verified:
                break
                
        mail.logout()
        
        if payment_verified:
            gateway_state["total_revenue"] += expected_amount
            timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
            tx_record = {"tx_id": tx_id, "amount": expected_amount, "status": "Approved", "time": timestamp}
            gateway_state["transactions"].insert(0, tx_record)
            return jsonify({"status": "approved", "message": "Verified", "tx_id": tx_id, "amount": expected_amount})
        else:
            return jsonify({"status": "pending", "message": "Pending payment."})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
