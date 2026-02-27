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
                "color": 0x5865F2,  # Discord blurple
                "footer": {
                    "text": "insight-mode daily digest"
                },
                "timestamp": None  # Will be set to current time
            }
        ]
        
        # Add up to 9 more insight embeds (Discord limit is 10 total)
        for i, ins in enumerate(insights[:9], 1):
            data = getattr(ins, "data", {}) or {}
            
            # Get title from data
            title = data.get("标题", data.get("title", data.get("Title", f"条目 {i}")))
            
            # Build description from data
            desc_parts = []
            for key, value in data.items():
                if key in ["标题", "title", "Title"]:
                    continue
                if isinstance(value, str):
                    desc_parts.append(f"**{key}**: {value[:200]}")
                elif isinstance(value, list):
                    list_str = ", ".join(str(v) for v in value[:3])
                    desc_parts.append(f"**{key}**: {list_str}")
            
            description = "\n".join(desc_parts[:5]) if desc_parts else "详见详情"  # Limit fields
            
            embeds.append({
                "title": title[:256] if title else f"条目 {i}",  # Discord title limit
                "description": description[:2048] if description else "No details",  # Discord desc limit
                "color": 0x7289DA,  # Light blue
            })
        
        if len(insights) > 9:
            embeds.append({
                "title": "更多洞察",
                "description": f"_还有 {len(insights) - 9} 条洞察未显示_",
                "color": 0x99AAB5,  # Grey
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
        
        # Build embeds
        embeds = self._format_embeds(insights, topic_name)
        
        # Build payload
        from datetime import datetime, timezone
        payload = {
            "content": None,
            "embeds": embeds,
            "username": "Insight Mode",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
        }
        
        # Add timestamp to first embed
        if embeds:
            embeds[0]["timestamp"] = datetime.now(timezone.utc).isoformat()
        
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
