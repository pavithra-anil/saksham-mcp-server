import logging
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from auth import get_creds

# ---------------- LOGGING SETUP ---------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------- MESSAGE BUILDER ---------------- #
def create_message(to: str, subject: str, body: str):
    """
    Creates a base64 encoded email message with HTML support.
    """
    try:
        # Check if body contains HTML
        is_html = body.strip().startswith("<!DOCTYPE") or body.strip().startswith("<html")

        if is_html:
            msg = MIMEMultipart("alternative")
            msg["to"] = to
            msg["subject"] = subject
            # Plain text fallback
            plain_text = "This email requires an HTML viewer to display correctly."
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(body, "html"))
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        else:
            message = MIMEText(body, "plain")
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        return {"raw": raw}
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise


# ---------------- MAIN FUNCTION ---------------- #
def create_email_draft(to: str, subject: str, body: str):
    """
    Creates a Gmail draft with HTML support.
    Args:
        to (str): Recipient email
        subject (str): Email subject
        body (str): Email body (plain text or HTML)
    Returns:
        dict: status + message
    """
    try:
        logger.info("Starting create_email_draft")

        # -------- INPUT VALIDATION -------- #
        if not to or not subject or not body:
            logger.error("Missing required email fields")
            return {
                "status": "error",
                "message": "to, subject, and body are required"
            }

        # -------- FORMAT BODY -------- #
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_html = body.strip().startswith("<!DOCTYPE") or body.strip().startswith("<html")

        if not is_html:
            # Only add timestamp to plain text emails
            formatted_body = f"[{timestamp}]\n{body}"
        else:
            formatted_body = body

        # -------- AUTH -------- #
        creds = get_creds()
        logger.info("Credentials loaded")

        # -------- INIT SERVICE -------- #
        service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail service initialized")

        # -------- CREATE MESSAGE -------- #
        message = create_message(to, subject, formatted_body)

        # -------- EXECUTE API CALL -------- #
        try:
            draft = service.users().drafts().create(
                userId="me",
                body={"message": message}
            ).execute()
            logger.info("Email draft created successfully")
            return {
                "status": "success",
                "message": "Draft created",
                "draft_id": draft.get("id")
            }
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return {
                "status": "error",
                "message": "Gmail API error",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                "status": "error",
                "message": "Failed during draft creation",
                "details": str(e)
            }

    # -------- FALLBACK ERROR -------- #
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "status": "error",
            "message": "Unexpected error occurred",
            "details": str(e)
        }