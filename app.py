
import streamlit as st
import jwt
import time
import re
import logging
from collections import defaultdict
import smtplib
from email.mime.text import MIMEText

# Load secrets
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]
ALLOWED_DOMAIN = st.secrets["ALLOWED_DOMAIN"]
GPTS_URL = st.secrets["GPTS_URL"]
SECRET_KEY = st.secrets["SECRET_KEY"]

# Setup request tracking
request_count = defaultdict(int)

# Setup logging
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

# Email sender
def send_email(to_email, link):
    msg = MIMEText(f"GPTs 포탈 접속 링크입니다. 아래 링크는 5분간 유효합니다:\n\n{link}")
    msg['Subject'] = "GPTs 인증 링크"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"이메일 전송 실패: {e}")
        return False

# Request count tracker
def increment_request_count(email):
    request_count[email] += 1
    logging.info(f"{email} has made {request_count[email]} requests")

# Query token handling
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

# Streamlit UI
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
            link = f"https://yourdomain.com/?token={token}"
            if send_email(email, link):
                logging.info(f"{email} requested link.")
                st.success("Access link has been sent to your email!")
