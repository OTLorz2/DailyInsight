"""
Email delivery plugin: read insights from InsightStore, send summary via SMTP.
Batch-type: called once per pipeline run.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from src.delivery.interface import DeliveryPlugin

logger = logging.getLogger(__name__)


def _build_body(insights: list[Any], raw_store: Any | None = None) -> str:
    """Build plain text email body from insights."""
    lines = ["# AI 洞察 日报\n"]
    for i, ins in enumerate(insights, 1):
        lines.append(f"## 条目 {i}\n")
        lines.append("- **商业机会**: " + ", ".join(ins.opportunities or ["-"]) + "\n")
        lines.append("- **技术方向**: " + ", ".join(ins.directions or ["-"]) + "\n")
        lines.append("- **创新点**: " + ", ".join(ins.innovations or ["-"]) + "\n")
        if raw_store and getattr(ins, "raw_item_id", None):
            raw = raw_store.get_by_id(ins.raw_item_id)
            if raw:
                lines.append(f"- **链接**: {raw.url}\n")
        lines.append("")
    return "\n".join(lines)


class EmailDeliveryPlugin(DeliveryPlugin):
    def __init__(self):
        self._plugin_id = "email"

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    def deliver(
        self,
        insight_store: Any,
        config: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        config = config or {}
        context = context or {}
        raw_store = context.get("raw_store")
        smtp_host = os.getenv("SMTP_HOST") or config.get("smtp_host")
        smtp_port = int(os.getenv("SMTP_PORT", "587") or config.get("smtp_port", "587"))
        smtp_user = os.getenv("SMTP_USER") or config.get("smtp_user")
        smtp_password = os.getenv("SMTP_PASSWORD") or config.get("smtp_password")
        smtp_from = os.getenv("SMTP_FROM") or config.get("smtp_from") or smtp_user
        email_to = os.getenv("EMAIL_TO") or config.get("email_to")
        subject_prefix = config.get("subject_prefix", "[AI 洞察]")
        if not all([smtp_host, smtp_user, smtp_password, email_to]):
            logger.warning("Email plugin: missing SMTP_HOST/USER/PASSWORD or EMAIL_TO")
            return False
        insights = insight_store.list_since(limit=100)
        if not insights:
            logger.info("Email plugin: no insights to send")
            return True
        body = _build_body(insights, raw_store)
        subject = f"{subject_prefix} 日报 {len(insights)} 条"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = email_to
        msg.attach(MIMEText(body, "plain", "utf-8"))
        use_ssl = smtp_port == 465
        try:
            if use_ssl:
                with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, [email_to], msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, [email_to], msg.as_string())
            logger.info("Email plugin: sent to %s", email_to)
            return True
        except Exception as e:
            logger.exception("Email plugin: send failed: %s", e)
            return False


# Config-driven loading: module exports this instance
plugin = EmailDeliveryPlugin()
