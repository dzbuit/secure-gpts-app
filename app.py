import streamlit as st
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse
import logging
from collections import defaultdict

# Load secrets
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]
ALLOWED_DOMAIN = st.secrets["ALLOWED_DOMAIN"]
GPTS_URL = st.secrets["GPTS_URL"]
BASE_URL = st.secrets["BASE_URL"]

# Logging
logging.basicConfig(filename="access.log", level=logging.INFO, format="%(asctime)s - %(message)s")
request_count = defaultdict(int)

# Validate email
def validate_email(email):
    pattern = rf"^[\w\.-]+@{ALLOWED_DOMAIN}$"
    return re.match(pattern, email)

# Send immediate redirect link email
def send_email(to_email):
    link = f"{GPTS_URL}"
    html = f"""
    <html>
      <body style="text-align:center; font-family:sans-serif;">
        <h2>🚀 GPTs 사내 포탈</h2>
        <p>아래 버튼을 클릭하면 바로 GPTs로 연결됩니다.</p>
        <a href="{link}" target="_blank" style="padding:14px 24px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:6px; font-size:16px;">
          GPTs 접속하기
        </a>
      </body>
    </html>
    """
    msg = MIMEMultipart("alternative")
    msg['Subject'] = "GPTs 바로가기 링크"
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

# UI
st.title("GPTs 사내 포탈")
email = st.text_input("사내 이메일 주소 입력")

if st.button("접속 요청"):
    if not validate_email(email):
        st.error("올바른 사내 이메일 주소를 입력하세요.")
    else:
        request_count[email] += 1
        logging.info(f"{email} 요청 {request_count[email]}회")
        if request_count[email] > 5:
            st.error("요청이 너무 많습니다. 잠시 후 다시 시도하세요.")
        else:
            if send_email(email):
                st.success("접속 링크가 이메일로 전송되었습니다.")
