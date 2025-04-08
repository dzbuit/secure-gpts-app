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

# Load secrets
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]
ALLOWED_DOMAIN = st.secrets["ALLOWED_DOMAIN"]
GPTS_URL = st.secrets["GPTS_URL"]
SECRET_KEY = st.secrets["SECRET_KEY"]
BASE_URL = st.secrets["BASE_URL"]  # ✅ 추가됨

# Setup request tracking
request_count = defaultdict(int)
logging.basicConfig(filename="access.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Token generator
def generate_token(email):
    payload = {
        "email": email,
        "exp": time.time() + 300,
        "access": "gpts"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Token validator
def validate_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload if payload.get("access") == "gpts" else None
    except jwt.ExpiredSignatureError:
        st.error("토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        st.error("유효하지 않은 토큰입니다.")
    return None

# Email validator
def validate_email(email):
    pattern = rf"^[\w\.-]+@{ALLOWED_DOMAIN}$"
    return re.match(pattern, email)

# Email sender with HTML format and encoded token
def send_email(to_email, token):
    safe_token = urllib.parse.quote(token)
    link = f"{BASE_URL}/?token={safe_token}"
    
    msg = MIMEMultipart("alternative")
    msg['Subject'] = "🔐 GPTs 인증 링크"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email

    html = f"""
    <html>
      <body>
        <p>GPTs 포탈 접속 링크입니다. 아래 버튼을 클릭하세요 (유효 시간: 5분):</p>
        <a href="{link}" target="_blank" style="padding:10px 15px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:5px;">🔗 GPTs 접속하기</a>
        <p>또는 직접 이 주소를 복사해 브라우저에 붙여넣으세요:<br>{link}</p>
      </body>
    </html>
    """

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

def increment_request_count(email):
    request_count[email] += 1
    logging.info(f"{email} has made {request_count[email]} requests")

# Query param으로 들어온 토큰 처리
query_params = st.experimental_get_query_params()
token = query_params.get("token", [None])[0]

if token:
    payload = validate_token(token)
    if payload:
        email = payload["email"]
        logging.info(f"{email} accessed GPTs.")
        st.success("인증 성공! GPTs로 이동합니다.")
        st.markdown(f"<meta http-equiv='refresh' content='2;url={GPTS_URL}'>", unsafe_allow_html=True)
    st.stop()

# 메인 UI
st.title("GPTs 사내 포탈")
email = st.text_input("사내 이메일 주소 입력")

if st.button("접속 요청"):
    if not validate_email(email):
        st.error("Invalid email address. Please use your corporate email.")
    else:
        increment_request_count(email)
        if request_count[email] > 5:
            st.error("요청이 너무 많습니다. 잠시 후 다시 시도하세요.")
        else:
            token = generate_token(email)
            if send_email(email, token):
                logging.info(f"{email} requested link.")
                st.success("Access link has been sent to your email!")
