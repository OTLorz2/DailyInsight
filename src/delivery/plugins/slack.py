"""
Slack delivery plugin: send insights summary to a Slack channel via incoming webhook.
"""
import json
import logging
import urllib.request
import urllib.parse
from typing import Any

from src.delivery.interface import DeliveryPlugin

logger = logging.getLogger(__name__)


class SlackDeliveryPlugin(DeliveryPlugin):
    def __init__(self):
        self._plugin_id = "slack"

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    def _format_blocks(self, insights: list[Any], topic_name: str) -> list[dict]:
        """Format insights into Slack Block Kit blocks."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{topic_name} 日报 - {len(insights)} 条洞察",
                    "emoji": True
                }
            },
            {"type": "divider"}
        ]
        
        for i, ins in enumerate(insights[:20], 1):  # Limit to 20 for Slack message limits
            data = getattr(ins, "data", {}) or {}
            
            # Build summary text from data
            summary_parts = []
            for key, value in data.items():
                if key.lower() in ["链接", "url", "link"]:
                    continue
                if isinstance(value, str):
                    summary_parts.append(f"*{key}*: {value[:200]}")
                elif isinstance(value, list):
                    summary_parts.append(f"*{key}*: {', '.join(str(v) for v in value[:3])}")
            
            summary_text = "\n".join(summary_parts) if summary_parts else "详见详情"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*条目 {i}*\n{summary_text}"
                }
            })
            
            if i < len(insights[:20]):
                blocks.append({"type": "divider"})
        
        if len(insights) > 20:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_还有 {len(insights) - 20} 条洞察未显示_"
                    }
                ]
            })
        
        return blocks

    def deliver(
        self,
        insight_store: Any,
        config: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Send insights to Slack via incoming webhook."""
        config = config or {}
        context = context or {}
        
        # Get configuration
        webhook_url = config.get("webhook_url")
        max_insights = int(config.get("max_insights", 20))
        
        # Get topic configuration
        topic_config = context.get("topic") or {}
        topic_name = topic_config.get("name", "洞察")
        
        if not webhook_url:
            logger.warning("Slack plugin: missing webhook_url in config")
            return False
        
        # Get insights
        insights = insight_store.list_since(limit=max_insights)
        if not insights:
            logger.info("Slack plugin: no insights to send")
            return True
        
        # Build message
        blocks = self._format_blocks(insights, topic_name)
        
        payload = {
            "text": f"{topic_name} 日报 - {len(insights)} 条洞察",
            "blocks": blocks
        }
        
        # Send to Slack
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "insight-mode/1.0"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    logger.info("Slack plugin: sent %d insights successfully", len(insights))
                    return True
                else:
                    logger.warning("Slack plugin: failed with status %d", resp.status)
                    return False
        except Exception as e:
            logger.exception("Slack plugin: send failed: %s", e)
            return False


# Config-driven loading: module exports this instance
plugin = SlackDeliveryPlugin()
