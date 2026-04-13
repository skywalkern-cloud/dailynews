import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import sys

# 读取 HTML 文件
with open('/Users/vincentnie/.openclaw/workspace-dailynews/gh-pages/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# SMTP Configuration
SMTP_HOST = "smtp.163.com"
SMTP_PORT = 465
SENDER_EMAIL = "fiveloong5@163.com"
SENDER_PASS = "BGVqCuAUzCc3cmnT"
RECIPIENT_EMAIL = "vincent_nie@foxmail.com"

# 创建邮件
msg = MIMEMultipart()
msg['From'] = Header(f"龙五 <{SENDER_EMAIL}>", 'utf-8')
msg['To'] = Header(RECIPIENT_EMAIL, 'utf-8')
msg['Subject'] = Header("📰 每日资讯 index.html - 2026-04-11", 'utf-8')

# 添加 HTML 内容
msg.attach(MIMEText(html_content, 'html', 'utf-8'))

try:
    print("Connecting to SMTP server...")
    server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    print("Logging in...")
    server.login(SENDER_EMAIL, SENDER_PASS)
    print("Sending email...")
    server.sendmail(SENDER_EMAIL, [RECIPIENT_EMAIL], msg.as_string())
    server.quit()
    print("✅ Email sent successfully!")
except Exception as e:
    print(f"❌ Error: {e}")