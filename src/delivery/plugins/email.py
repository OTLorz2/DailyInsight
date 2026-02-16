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


def _parse_recipients(raw: str | list[str] | None) -> list[str]:
    """Parse EMAIL_TO / email_to into list of addresses (comma-separated string or list)."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [s.strip() for s in raw if s and s.strip()]
    return [s.strip() for s in str(raw).split(",") if s.strip()]


def _format_value(v: Any) -> str:
    """Format a single value for email: list -> join, str -> as is, dict -> one line summary."""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) if v else "-"
    if isinstance(v, str):
        return v or "-"
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_format_value(val)}" for k, val in v.items()) or "-"
    return str(v) if v is not None else "-"


def _build_body(insights: list[Any], raw_store: Any | None = None) -> str:
    """Build plain text email body from insights (flexible data structure)."""
    lines = ["# AI 洞察 日报\n"]
    for i, ins in enumerate(insights, 1):
        lines.append(f"## 条目 {i}\n")
        data = getattr(ins, "data", {}) or {}
        for key, value in data.items():
            label = key.replace("_", " ").strip()
            lines.append(f"- **{label}**: {_format_value(value)}\n")
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
        email_to_raw = os.getenv("EMAIL_TO") or config.get("email_to")
        recipients = _parse_recipients(email_to_raw)
        subject_prefix = config.get("subject_prefix", "[AI 洞察]")
        max_insights = int(config.get("max_insights", 100))
        if not all([smtp_host, smtp_user, smtp_password]) or not recipients:
            logger.warning("Email plugin: missing SMTP_HOST/USER/PASSWORD or EMAIL_TO")
            return False
        insights = insight_store.list_since(limit=max_insights)
        if not insights:
            logger.info("Email plugin: no insights to send")
            return True
        body = _build_body(insights, raw_store)
        subject = f"{subject_prefix} 日报 {len(insights)} 条"
        use_ssl = smtp_port == 465
        try:
            if use_ssl:
                with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                    server.login(smtp_user, smtp_password)
                    for to in recipients:
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = subject
                        msg["From"] = smtp_from
                        msg["To"] = to
                        msg.attach(MIMEText(body, "plain", "utf-8"))
                        server.sendmail(smtp_from, [to], msg.as_string())
                        logger.info("Email plugin: sent to %s", to)
            else:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    for to in recipients:
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = subject
                        msg["From"] = smtp_from
                        msg["To"] = to
                        msg.attach(MIMEText(body, "plain", "utf-8"))
                        server.sendmail(smtp_from, [to], msg.as_string())
                        logger.info("Email plugin: sent to %s", to)
            return True
        except Exception as e:
            logger.exception("Email plugin: send failed: %s", e)
            return False


# Config-driven loading: module exports this instance
plugin = EmailDeliveryPlugin()
