from utils.utils import *

EMAIL_ACCOUNT = "chi0514@mindnodeair.com"
EMAIL_APP_PASSWORD = "jalg sloz jpgm ekvw"

def send_reset_email(to_email, reset_link):
    try:
        msg = MIMEText(f"請點選以下連結以重設密碼：{reset_link}", "plain", "utf-8")
        msg["Subject"] = "密碼重設連結"
        msg["From"] = EMAIL_ACCOUNT
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ACCOUNT, EMAIL_APP_PASSWORD)
            server.send_message(msg)
            return True
    except:
        return False