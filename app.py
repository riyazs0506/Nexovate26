from flask import (
    Flask, render_template, request,
    redirect, session, flash, send_file
)
from flask_mail import Mail, Message
import pymysql
import uuid
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ================= DATABASE CONNECTION =================
def get_db():
    return pymysql.connect(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

# ================= MAIL CONFIG =================
# ================= MAIL CONFIG =================
app.config.update(
    MAIL_SERVER=config.MAIL_SERVER,
    MAIL_PORT=config.MAIL_PORT,
    MAIL_USE_TLS=config.MAIL_USE_TLS,
    MAIL_USERNAME=config.MAIL_USERNAME,
    MAIL_PASSWORD=config.MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER=config.MAIL_DEFAULT_SENDER
)

mail = Mail(app)

# ================= MAIL HELPER =================
def send_async_mail(msg):
    try:
        mail.send(msg)
    except Exception as e:
        print("Mail error:", e)


# ================= HOME =================
@app.route('/')
def home():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) AS total FROM teams WHERE transaction_id IS NOT NULL"
    )
    total_registrations = cur.fetchone()['total']

    cur.close()
    conn.close()

    return render_template(
        'home.html',
        total_registrations=total_registrations
    )

# ================= USER REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        try:
            conn = get_db()
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
                (name, email, password)
            )

            msg = Message(
                "NEXOVATE'26 Registration Successful",
                recipients=[email]
            )
            msg.body = f"""
Hello {name},

You have successfully registered for NEXOVATE'26.

Next step:
Login → Register Event → Payment

Regards,
NEXOVATE'26 Team
"""
            send_async_mail(msg)


            flash("Registration successful! Check your email.", "success")
            return redirect('/login')

        except pymysql.err.IntegrityError:
            flash("Email already registered", "danger")
            return redirect('/register')

        finally:
            cur.close()
            conn.close()

    return render_template('auth/register.html')

# ================= USER LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session['user'] = email
            return redirect('/user/dashboard')

        flash("Invalid email or password", "danger")

    return render_template('auth/login.html')

# ================= USER DASHBOARD =================
@app.route('/user/dashboard')
def user_dashboard():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM teams WHERE leader_email=%s",
        (session['user'],)
    )
    team = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        'user/dashboard.html',
        team=team
    )

# ================= REGISTER EVENT =================
@app.route('/user/register-event')
def register_event():
    if 'user' not in session:
        return redirect('/login')
    return redirect('/team')

# ================= TEAM REGISTRATION =================
@app.route('/team', methods=['GET', 'POST'])
def team():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        reg_type = request.form.get('reg_type')
        team_name = request.form.get('team_name')

        names = request.form.getlist('member_name[]')
        phones = request.form.getlist('phone[]')
        emails = request.form.getlist('college_email[]')

        members = [
            (n.strip(), p.strip(), e.strip())
            for n, p, e in zip(names, phones, emails)
            if n and p and e
        ]
        # ===== AMOUNT CALCULATION =====
        amount_paid = len(members) * 250
        session['amount_paid'] = amount_paid


        # ===== RULES =====
        if reg_type == "workshop":
            if len(members) != 1:
                flash("Workshop allows exactly 1 participant", "danger")
                return redirect('/team')
            team_name = None

        elif reg_type in ("workshop_technical", "technical_nontechnical"):
            if not (2 <= len(members) <= 3):
                flash("Team must have 2 to 3 members", "danger")
                return redirect('/team')
            if not team_name:
                flash("Team name required", "danger")
                return redirect('/team')

        else:
            flash("Select a valid registration option", "danger")
            return redirect('/team')

        if len(set(m[0].lower() for m in members)) != len(members):
            flash("Duplicate member names not allowed", "danger")
            return redirect('/team')

        team_id = "NX" + str(uuid.uuid4())[:6].upper()

        try:
            conn = get_db()
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO teams
                (team_id, team_name, leader_email, registration_type)
                VALUES (%s, %s, %s, %s)
                """,
                (team_id, team_name, session['user'], reg_type)
            )

            for m in members:
                for index, m in enumerate(members, start=1):
                    student_id = f"{team_id}-{index:02d}"

                    cur.execute(
                        """
                        INSERT INTO members
                        (team_id, student_id, member_name, phone, college_email)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (team_id, student_id, m[0], m[1], m[2])
                    )



            return redirect(f'/payment/{team_id}')

        except pymysql.err.IntegrityError:
            flash("Phone or email already used", "danger")
            return redirect('/team')

        finally:
            cur.close()
            conn.close()

    return render_template('user/team_register.html')

# ================= PAYMENT =================
@app.route('/payment/<team_id>', methods=['GET', 'POST'])
def payment(team_id):
    if request.method == 'POST':
        txn = request.form['transaction_id']

        conn = get_db()
        cur = conn.cursor()

        amount = session.get('amount_paid', 0)

        cur.execute(
            """
            UPDATE teams
            SET transaction_id=%s,
                payment_status='WAITING',
                amount_paid=%s
            WHERE team_id=%s
            """,
            (txn, amount, team_id)
        )


        cur.close()
        conn.close()

        flash("Payment submitted. Await admin approval.", "info")
        return redirect(f'/status/{team_id}')

    return render_template('user/payment.html', team_id=team_id)

# ================= STATUS =================
@app.route('/status/<team_id>')
def status(team_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM teams WHERE team_id=%s",
        (team_id,)
    )
    team = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('user/status.html', team=team)

# ================= CERTIFICATE =================
@app.route('/certificate')
def certificate():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT team_id, certificate_enabled
        FROM teams WHERE leader_email=%s
        """,
        (session['user'],)
    )
    team = cur.fetchone()

    cur.close()
    conn.close()

    if not team or team['certificate_enabled'] != 1:
        flash("Certificate not enabled by admin", "warning")
        return redirect('/user/dashboard')

    return send_file(
        f"static/certificates/{team['team_id']}.pdf",
        as_attachment=True
    )

# ================= ADMIN LOGIN =================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (u, p)
        )

        if cur.fetchone():
            session['admin'] = u
            return redirect('/admin/dashboard')

        flash("Invalid admin credentials", "danger")

        cur.close()
        conn.close()

    return render_template('admin/login.html')

# ================= ADMIN DASHBOARD =================
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM teams")
    teams = cur.fetchall()

    for t in teams:
        cur.execute(
            "SELECT student_id, member_name, phone, college_email FROM members WHERE team_id=%s",
            (t['team_id'],)
        )
        t['members'] = cur.fetchall()

    cur.execute(
        "SELECT COUNT(*) AS total FROM teams WHERE transaction_id IS NOT NULL"
    )
    total_paid = cur.fetchone()['total']

    cur.execute(
        "SELECT COUNT(*) AS pending FROM teams WHERE payment_status='WAITING'"
    )
    pending_count = cur.fetchone()['pending']

    cur.close()
    conn.close()

    return render_template(
        'admin/dashboard.html',
        teams=teams,
        total_paid=total_paid,
        pending_count=pending_count
    )

# ================= APPROVE PAYMENT =================
@app.route('/approve/<team_id>')
def approve(team_id):
    if 'admin' not in session:
        return redirect('/admin/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT leader_email FROM teams WHERE team_id=%s",
        (team_id,)
    )
    email = cur.fetchone()['leader_email']

    cur.execute(
        "UPDATE teams SET payment_status='APPROVED' WHERE team_id=%s",
        (team_id,)
    )

    msg = Message(
        "NEXOVATE'26 Payment Approved",
        recipients=[email]
    )
    msg.body = f"""
Payment approved!

Your Team ID: {team_id}

Regards,
NEXOVATE'26 Team
"""
    send_async_mail(msg)


    cur.close()
    conn.close()

    flash("Payment approved", "success")
    return redirect('/admin/dashboard')

# ================= ENABLE CERTIFICATE =================
@app.route('/admin/enable-certificate/<team_id>')
def enable_certificate(team_id):
    if 'admin' not in session:
        return redirect('/admin/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE teams SET certificate_enabled=1 WHERE team_id=%s",
        (team_id,)
    )

    cur.close()
    conn.close()

    flash("Certificate enabled", "success")
    return redirect('/admin/dashboard')

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect('/')

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)
