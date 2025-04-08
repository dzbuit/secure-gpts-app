import streamlit as st
import jwt
import time
import re
import logging
from collections import defaultdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse

# Load secrets from .streamlit/secrets.toml
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]
ALLOWED_DOMAIN = st.secrets["ALLOWED_DOMAIN"]
GPTS_URL = st.secrets["GPTS_URL"]
SECRET_KEY = st.secrets["SECRET_KEY"]
BASE_URL = st.secrets["BASE_URL"]

# Request count tracking
request_count = defaultdict(int)

# Logging
logging.basicConfig(filename="access.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Generate JWT token
def generate_token(email):
    payload = {
        "email": email,
        "exp": time.time() + 300,
        "access": "gpts"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Validate JWT token
def validate_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload if payload.get("access") == "gpts" else None
    except jwt.ExpiredSignatureError:
        st.error("토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        st.error("유효하지 않은 토큰입니다.")
    return None

# Validate corporate email
def validate_email(email):
    pattern = rf"^[\w\.-]+@{ALLOWED_DOMAIN}$"
    return re.match(pattern, email)

# Send email with simple button-only HTML
def send_email(to_email, token):
    safe_token = urllib.parse.quote(token)
    link = f"{BASE_URL}/?token={safe_token}"

    html = f"""
    <html>
      <body style="text-align:center; font-family:sans-serif;">
        <h2>🔐 GPTs 사내 포탈 접속</h2>
        <p style="margin-bottom: 30px;">아래 버튼을 클릭하면 GPTs에 바로 연결됩니다.</p>
        <a href="{link}" target="_blank" style="padding:14px 24px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:6px; font-size:16px;">
          🚀 GPTs 접속하기
        </a>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg['Subject'] = "GPTs 접속 링크"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"이메일 전송 실패: {e}")
        return False

# Count user requests
def increment_request_count(email):
    request_count[email] += 1
    logging.info(f"{email} has made {request_count[email]} requests")

# 🔐 Handle token access via URL param
token = st.query_params.get("token", [None])[0]

if token:
    payload = validate_token(token)
    if payload:
        email = payload["email"]
        logging.info(f"{email} accessed GPTs.")
        st.success("인증 성공! GPTs로 이동합니다.")
        st.markdown(f"<meta http-equiv='refresh' content='2;url={GPTS_URL}'>", unsafe_allow_html=True)
    st.stop()

# UI
st.title("GPTs 사내 포탈")
email = st.text_input("사내 이메일 주소 입력")

if st.button("접속 요청"):
    if not validate_email(email):
        st.error("올바른 사내 이메일 주소를 입력하세요.")
    else:
        increment_request_count(email)
        if request_count[email] > 5:
            st.error("요청이 너무 많습니다. 잠시 후 다시 시도하세요.")
        else:
            token = generate_token(email)
            if send_email(email, token):
                logging.info(f"{email} requested access.")
                st.success("접속 링크가 이메일로 전송되었습니다.")
