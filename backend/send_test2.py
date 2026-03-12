import smtplib, sys, json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

sys.path.insert(0, '.')
from database.db_manager import DatabaseManager

db = DatabaseManager()

# Load SMTP settings from DB
rows = db.execute_query(
    'SELECT value_data FROM system_metadata WHERE key_name = %s LIMIT 1',
    ('admin_notification_preferences',)
)
data = rows[0]['value_data']
if isinstance(data, str):
    data = json.loads(data)

smtp_server   = data.get('smtpServer', '').strip()
smtp_port     = int(data.get('smtpPort', 587))
smtp_user     = data.get('smtpUser', '').strip()
smtp_password = data.get('smtpPassword', '').strip()
admin_email   = data.get('adminEmail', '').strip()
to_email      = admin_email or smtp_user

# Load real deforested areas from DB
areas = db.execute_query("""
    SELECT ma.id, ma.name, ma.last_monitored, ma.detection_count,
           dh.forest_loss_percent, dh.forest_cover_before, dh.forest_cover_after,
           dh.before_date, dh.after_date, dh.vegetation_trend
    FROM monitored_areas ma
    JOIN detection_history dh ON dh.area_id = ma.id
    WHERE dh.deforestation_detected = 1
    ORDER BY dh.timestamp DESC
""") or []

print(f"Found {len(areas)} deforested area(s) in database")

rows_html = ""
for area in areas:
    loss         = float(area.get('forest_loss_percent') or 0)
    cover_before = float(area.get('forest_cover_before') or 0)
    cover_after  = float(area.get('forest_cover_after') or 0)
    before_date  = str(area.get('before_date') or '')
    after_date   = str(area.get('after_date') or '')
    trend        = str(area.get('vegetation_trend') or 'decline').title()
    name         = area.get('name') or 'Unknown Area'
    last_mon     = str(area.get('last_monitored') or '')[:10]
    rows_html += (
        '<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:6px;padding:16px;margin:12px 0;">'
        f'<p style="margin:0 0 8px 0;font-weight:bold;font-size:15px;color:#991b1b;">&#9888; {name}</p>'
        '<table style="width:100%;font-size:13px;color:#374151;border-collapse:collapse;">'
        f'<tr><td style="padding:3px 0;font-weight:600;width:180px;">Forest Loss:</td><td style="color:#dc2626;font-weight:bold;">{loss:.2f}%</td></tr>'
        f'<tr><td style="padding:3px 0;font-weight:600;">Forest Cover Before:</td><td>{cover_before:.4f} km2</td></tr>'
        f'<tr><td style="padding:3px 0;font-weight:600;">Forest Cover After:</td><td>{cover_after:.4f} km2</td></tr>'
        f'<tr><td style="padding:3px 0;font-weight:600;">Vegetation Trend:</td><td>{trend}</td></tr>'
        f'<tr><td style="padding:3px 0;font-weight:600;">Detection Period:</td><td>{before_date} to {after_date}</td></tr>'
        f'<tr><td style="padding:3px 0;font-weight:600;">Last Monitored:</td><td>{last_mon}</td></tr>'
        '<tr><td style="padding:3px 0;font-weight:600;">Status:</td>'
        '<td><span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:9999px;font-size:12px;">Awaiting Response</span></td></tr>'
        '</table></div>'
    )

if not rows_html:
    rows_html = "<p style='color:#6b7280;'>No deforestation records found in the database yet.</p>"

now_str = datetime.now().strftime("%B %d, %Y at %H:%M UTC")
body_html = (
    '<div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;background:#f9fafb;padding:24px;border-radius:8px;">'
    '<div style="background:#b91c1c;color:#fff;padding:16px 20px;border-radius:6px 6px 0 0;">'
    '<h2 style="margin:0;font-size:18px;">&#9888; DEFORESTATION DETECTION ALERT</h2>'
    f'<p style="margin:6px 0 0 0;font-size:13px;opacity:0.85;">ML Deforestation Monitoring System &mdash; {now_str}</p>'
    '</div>'
    '<div style="background:#fff;border:1px solid #e5e7eb;border-top:none;padding:20px;border-radius:0 0 6px 6px;">'
    '<p style="color:#374151;font-size:14px;">This is a <strong>test alert</strong> showing real deforestation data from your database.</p>'
    + rows_html +
    '<p style="color:#6b7280;font-size:12px;margin-top:20px;border-top:1px solid #e5e7eb;padding-top:12px;">'
    'This is an automated alert from the ML Deforestation Monitoring System.<br/>'
    'Log in to the system to view full details, satellite images, and respond to alerts.'
    '</p></div></div>'
)

msg = MIMEMultipart("alternative")
msg["From"]     = f"ML Deforestation Monitoring System <{admin_email}>"
msg["To"]       = to_email
msg["Reply-To"] = admin_email
msg["Subject"]  = f"ML Deforestation Monitoring System - Detection Alert ({len(areas)} area(s) flagged)"
msg.attach(MIMEText(body_html, "html"))

print(f"Sending to   : {to_email}")
print(f"SMTP server  : {smtp_server}:{smtp_port}")

try:
    with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
    print("SUCCESS - check inbox AND spam/junk folder")
except Exception as e:
    print(f"FAILED: {e}")
