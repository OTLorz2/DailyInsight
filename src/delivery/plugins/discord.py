"""
Discord delivery plugin: send insights summary to a Discord channel via webhook.
"""
import json
import logging
import urllib.request
from typing import Any

from src.delivery.interface import DeliveryPlugin

logger = logging.getLogger(__name__)


class DiscordDeliveryPlugin(DeliveryPlugin):
    def __init__(self):
        self._plugin_id = "discord"

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    def _format_embeds(self, insights: list[Any], topic_name: str) -> list[dict]:
        """Format insights into Discord embeds."""
        embeds = [
            {
                "title": f"{topic_name} 日报",
                "description": f"今日共 **{len(insights)}** 条洞察",
                "color": 0x00BFFF,  # Deep sky blue
                "footer": {
                    "text": "insight-mode daily digest"
                }
            }
        ]
        
        # Add up to 10 insight embeds (Discord limit is 10 embeds per message)
        for i, ins in enumerate(insights[:10], 1):
            data = getattr(ins, "data", {}) or {}
            
            # Build description from data
            desc_parts = []
            for key, value in data.items():
                if key.lower() in ["链接", "url", "link"]:
                    continue
                if isinstance(value, str):
                    desc_parts.append(f"**{key}**: {value[:150]}")
                elif isinstance(value, list):
                    list_str = ", ".join(str(v) for v in value[:3])
                    desc_parts.append(f"**{key}**: {list_str}")
            
            description = "\n".join(desc_parts) if desc_parts else "详见详情"
            
            embeds.append({
                "title": f"条目 {i}",
                "description": description,
                "color": 0x7289DA,  # Discord blurple
            })
        
        if len(insights) > 10:
            embeds.append({
                "title": "更多洞察",
                "description": f"_还有 {len(insights) - 10} 条洞察未显示_",
                "color": 0x99AAB5,  # Discord grey
            })
        
        return embeds

    def deliver(
        self,
        insight_store: Any,
        config: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Send insights to Discord via webhook."""
        config = config or {}
        context = context or {}
        
        # Get configuration
        webhook_url = config.get("webhook_url")
        max_insights = int(config.get("max_insights", 10))
        
        # Get topic configuration
        topic_config = context.get("topic") or {}
        topic_name = topic_config.get("name", "洞察")
        
        if not webhook_url:
            logger.warning("Discord plugin: missing webhook_url in config")
            return False
        
        # Get insights
        insights = insight_store.list_since(limit=max_insights)
        if not insights:
            logger.info("Discord plugin: no insights to send")
            return True
        
        # Build payload
        embeds = self._format_embeds(insights, topic_name)
        
        payload = {
            "content": None,
            "embeds": embeds
        }
        
        # Send to Discord
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
                if resp.status in [200, 204]:
                    logger.info("Discord plugin: sent %d insights successfully", len(insights))
                    return True
                else:
                    body = resp.read().decode("utf-8")
                    logger.warning("Discord plugin: failed with status %d: %s", resp.status, body)
                    return False
        except Exception as e:
            logger.exception("Discord plugin: send failed: %s", e)
            return False


# Config-driven loading: module exports this instance
plugin = DiscordDeliveryPlugin()
