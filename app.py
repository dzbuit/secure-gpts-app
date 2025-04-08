import streamlit as st
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
from datetime import datetime
import csv
import os

# Load secrets
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]
ALLOWED_DOMAIN = st.secrets["ALLOWED_DOMAIN"]
GPTS_URL = st.secrets["GPTS_URL"]
ADMIN_SECRET_PREFIX = "GNK+"

# 해시된 사용자 저장용 Set
user_hash_set = set()
LOG_FILE = "user_requests.csv"

# CSV 로드
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                user_hash_set.add(row[0])

# 이메일 유효성 검사
def validate_email(email):
    pattern = rf"^[\w\.-]+@{ALLOWED_DOMAIN}$"
    return re.match(pattern, email)

# 이메일 해시화 (비식별)
def anonymize_email(email):
    return hashlib.sha256(email.encode()).hexdigest()

# CSV 저장
def log_request(email_hash):
    today = datetime.today().strftime("%Y-%m-%d")
    with open(LOG_FILE, "a") as f:
        writer = csv.writer(f)
        writer.writerow([email_hash, today])

# 날짜별 요청 통계 생성
def summarize_requests():
    stats = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    date = row[1]
                    stats[date] = stats.get(date, 0) + 1
    return stats

# 사용자 이메일로 전송
def send_user_email(to_email, user_count):
    link = f"{GPTS_URL}"
    html = f"""
    <html>
      <body style="text-align:center; font-family:sans-serif; padding: 20px;">
        <h2>🚀 GPTs 사내 포탈 링크</h2>
        <p style="margin-bottom: 20px; font-size: 14px; color: #444;">
          아래 버튼을 클릭하면 GPTs에 접속할 수 있습니다.<br>
          지금까지 <b>{user_count}</b>명의 사내 사용자가 이용했습니다.
        </p>
        <a href="{link}" target="_blank"
           style="display: inline-block; padding: 14px 24px; background-color: #4CAF50;
                  color: white; text-decoration: none; border-radius: 6px; font-size: 16px;">
          GPTs 접속하기
        </a>
      </body>
    </html>
    """
    return send_email(to_email, html, "GPTs 링크 안내")

# 관리자용 통계 메일 전송
def send_admin_email(to_email, stats, user_count):
    rows = "".join(f"<tr><td>{date}</td><td>{count}</td></tr>" for date, count in stats.items())
    html = f"""
    <html>
      <body style="font-family:sans-serif; padding: 20px;">
        <h2>🧠 GPTs 접속 요청 통계</h2>
        <p>총 유저 수: <b>{user_count}</b></p>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>날짜</th><th>요청 수</th></tr>
          {rows}
        </table>
      </body>
    </html>
    """
    return send_email(to_email, html, "GPTs 요청 통계")

# 메일 발송 공통
def send_email(to_email, html_content, subject):
    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg.attach(MIMEText(html_content, "html"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"이메일 전송 실패: {e}")
        return False

# UI
st.title("GNK GPTs 링크 포탈")
email = st.text_input("사내 이메일을 입력하세요:")

if st.button("요청"):
    if not validate_email(email):
        st.error("gnk.or.kr 도메인의 이메일만 입력 가능합니다.")
    else:
        if email.startswith(ADMIN_SECRET_PREFIX):
            stats = summarize_requests()
            user_count = len(user_hash_set)
            if send_admin_email(email, stats, user_count):
                st.success("관리자 통계 이메일이 전송되었습니다.")
        else:
            hashed = anonymize_email(email)
            if hashed not in user_hash_set:
                user_hash_set.add(hashed)
                log_request(hashed)
            user_count = len(user_hash_set)
            if send_user_email(email, user_count):
                st.success("GPTs 접속 링크가 전송되었습니다.")
