from flask import (
    Flask, render_template, request,
    redirect, session, flash
)
from flask_mail import Mail, Message
import pymysql
import uuid
import os
import secrets   # ✅ REQUIRED (FIXED)

app = Flask(__name__)

# ================= SECRET KEY =================
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

# ================= DATABASE CONNECTION =================
def get_db():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        ssl={"ssl": {}}  # ✅ REQUIRED for Aiven / cloud MySQL
    )

# ================= MAIL CONFIG =================
app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() == "true",
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER")
)

mail = Mail(app)

def send_mail(msg):
    try:
        mail.send(msg)
    except Exception as e:
        print("Mail error:", e)

# ================= HOME =================
@app.route('/')
def home():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM teams WHERE transaction_id IS NOT NULL")
    total = cur.fetchone()['total']
    cur.close()
    conn.close()
    return render_template('home.html', total_registrations=total)

# ================= WORKSHOP LIMIT =================
def workshop_full(workshop_name):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) AS c
        FROM workshop_registrations
        WHERE workshop_name=%s
    """, (workshop_name,))
    count = cur.fetchone()['c']
    cur.close()
    conn.close()
    return count >= 30

# ================= TEAM REGISTRATION =================
@app.route('/team', methods=['GET', 'POST'])
def team():
    if request.method == 'POST':

        # ---------- MEMBER DETAILS ----------
        names = request.form.getlist('member_name[]')
        years = request.form.getlist('study_year[]')
        depts = request.form.getlist('department[]')
        colleges = request.form.getlist('college_name[]')
        phones = request.form.getlist('phone[]')
        emails = request.form.getlist('college_email[]')

        members = []
        for n, y, d, c, p, e in zip(names, years, depts, colleges, phones, emails):
            if n and y and d and c and p and e:
                members.append((n.strip(), y, d, c, p, e))

        if not members:
            flash("At least one member is required", "danger")
            return redirect('/team')

        leader_name = members[0][0]
        leader_email = members[0][5]

        reg_type = request.form['reg_type']
        team_name = request.form.get('team_name')
        member_count = len(members)

        # ---------- WORKSHOPS ----------
        workshops = request.form.getlist('workshop_choice[]')

        for w in workshops:
            if w and workshop_full(w):
                flash(f"{w} workshop is already full (30/30)", "danger")
                return redirect('/team')

        # ---------- TEAM SIZE ----------
        if reg_type == "technical_nontech_workshop":
            if member_count > 3:
                flash("Max 3 members allowed (IPL Auction rule)", "danger")
                return redirect('/team')
        else:
            if not (1 <= member_count <= 2):
                flash("Max 2 members allowed", "danger")
                return redirect('/team')

        # ---------- IDS ----------
        team_id = "NX" + uuid.uuid4().hex[:6].upper()
        token = secrets.token_urlsafe(24)
        amount = member_count * 250

        try:
            conn = get_db()
            cur = conn.cursor()

            # ---------- TEAM ----------
            cur.execute("""
                INSERT INTO teams
                (team_id, team_name, leader_name, leader_email,
                 registration_type, member_count,
                 amount_paid, payment_status, status_token)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDING',%s)
            """, (
                team_id, team_name, leader_name, leader_email,
                reg_type, member_count, amount, token
            ))

            # ---------- MEMBERS ----------
            member_ids = []
            for i, m in enumerate(members, start=1):
                student_id = f"{team_id}-{i:02d}"

                cur.execute("""
                    INSERT INTO members
                    (team_id, student_id, member_name,
                     study_year, department, college_name,
                     phone, college_email)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    team_id, student_id,
                    m[0], m[1], m[2], m[3], m[4], m[5]
                ))

                member_ids.append(cur.lastrowid)

            # ---------- TEAM EVENTS ----------
            tech_events = request.form.getlist('tech_events[]')
            nontech_events = request.form.getlist('nontech_events[]')

            for ev in tech_events:
                cur.execute("""
                    INSERT INTO team_events (team_id, event_name, event_category)
                    VALUES (%s,%s,'technical')
                """, (team_id, ev))

            for ev in nontech_events:
                cur.execute("""
                    INSERT INTO team_events (team_id, event_name, event_category)
                    VALUES (%s,%s,'non_technical')
                """, (team_id, ev))

            # ---------- WORKSHOP REGISTRATIONS ----------
            while len(workshops) < len(member_ids):
                workshops.append(None)

            for mid, w in zip(member_ids, workshops):
                if w:
                    cur.execute("""
                        INSERT INTO workshop_registrations (member_id, workshop_name)
                        VALUES (%s,%s)
                    """, (mid, w))

            # ---------- EMAIL ----------
            msg = Message(
                "NEXOVATE'26 – Registration Received",
                recipients=[leader_email]
            )
            msg.body = f"""
Hello {leader_name},

Your registration is successful.

Team ID: {team_id}
Members: {member_count}
Amount to Pay: ₹{amount}

Proceed to payment:
https://yourdomain.com/payment/{team_id}

Regards,
NEXOVATE'26 Team
"""
            send_mail(msg)

            return redirect(f'/payment/{team_id}')

        finally:
            cur.close()
            conn.close()

    return render_template('team_register.html')

# ================= PAYMENT =================
@app.route('/payment/<team_id>', methods=['GET', 'POST'])
def payment(team_id):
    if request.method == 'POST':
        txn = request.form['transaction_id']

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            UPDATE teams
            SET transaction_id=%s, payment_status='WAITING'
            WHERE team_id=%s
        """, (txn, team_id))

        cur.execute("""
            SELECT leader_email, status_token
            FROM teams WHERE team_id=%s
        """, (team_id,))
        data = cur.fetchone()

        msg = Message(
            "NEXOVATE'26 – Payment Received",
            recipients=[data['leader_email']]
        )
        msg.body = f"""
Payment received successfully.

Status: WAITING (Admin Approval Pending)

Check status:
https://yourdomain.com/status-check/{data['status_token']}
"""
        send_mail(msg)

        cur.close()
        conn.close()

        flash("Payment submitted successfully.", "success")
        return redirect('/')

    return render_template('payment.html', team_id=team_id)

# ================= STATUS =================
@app.route('/status-check/<token>')
def status_check(token):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT team_id, payment_status, amount_paid
        FROM teams WHERE status_token=%s
    """, (token,))
    team = cur.fetchone()
    cur.close()
    conn.close()

    if not team:
        flash("Invalid link", "danger")
        return redirect('/')

    return render_template('status.html', team=team)

# ================= ADMIN =================
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
            return redirect('/admin/dashboard')

        flash("Invalid credentials", "danger")

    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            t.*,
            GROUP_CONCAT(te.event_name SEPARATOR ', ') AS events
        FROM teams t
        LEFT JOIN team_events te ON t.team_id = te.team_id
        GROUP BY t.team_id
        ORDER BY t.created_at DESC
    """)
    teams = cur.fetchall()

    # ✅ ATTACH MEMBERS
    for t in teams:
        cur.execute("""
            SELECT student_id, member_name, phone, college_email
            FROM members
            WHERE team_id=%s
            ORDER BY student_id
        """, (t['team_id'],))
        t['members'] = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS c FROM teams WHERE payment_status='APPROVED'")
    total_paid = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) AS c FROM teams WHERE payment_status='WAITING'")
    pending_count = cur.fetchone()['c']

    cur.close()
    conn.close()

    return render_template(
        'admin/dashboard.html',
        teams=teams,
        total_paid=total_paid,
        pending_count=pending_count
    )

@app.route('/approve/<team_id>')
def approve(team_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE teams
        SET payment_status='APPROVED'
        WHERE team_id=%s
    """, (team_id,))

    cur.execute("""
        SELECT leader_email, status_token
        FROM teams WHERE team_id=%s
    """, (team_id,))
    data = cur.fetchone()

    msg = Message(
        "NEXOVATE'26 – Payment Approved 🎉",
        recipients=[data['leader_email']]
    )
    msg.body = f"""
Your payment is APPROVED 🎉

Check status:
https://yourdomain.com/status-check/{data['status_token']}
"""
    send_mail(msg)

    cur.close()
    conn.close()
    return redirect('/admin/dashboard')

# ================= RUN =================
if __name__ == "__main__":
    app.run()
