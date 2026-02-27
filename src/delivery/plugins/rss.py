"""
RSS Feed delivery plugin: generate an RSS feed file of insights.
This creates a static RSS file that can be served by a web server or CDN.
"""
import logging
import os
from datetime import datetime
from email.utils import format_datetime
from typing import Any
from xml.sax.saxutils import escape

from src.delivery.interface import DeliveryPlugin

logger = logging.getLogger(__name__)


class RSSDeliveryPlugin(DeliveryPlugin):
    def __init__(self):
        self._plugin_id = "rss"

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return escape(text, {'"': "&quot;", "'": "&apos;"})

    def _format_rss_item(self, insight: Any, raw_store: Any) -> str:
        """Format a single insight as an RSS item."""
        data = getattr(insight, "data", {}) or {}
        raw_item_id = getattr(insight, "raw_item_id", None)
        analyzed_at = getattr(insight, "analyzed_at", datetime.utcnow().isoformat())
        
        # Get title from data or fetch from raw_store
        title = data.get("标题", data.get("title", data.get("Title", "Insight")))
        
        # Get URL from raw_store if available
        url = ""
        if raw_store and raw_item_id:
            raw = raw_store.get_by_id(raw_item_id)
            if raw:
                url = raw.url
                # Use raw title if not found in data
                if not title:
                    title = raw.title
        
        # Build description from data
        desc_parts = []
        for key, value in data.items():
            if key in ["标题", "title", "Title"]:
                continue
            if isinstance(value, str):
                desc_parts.append(f"&lt;strong&gt;{key}:&lt;/strong&gt; {value}")
            elif isinstance(value, list):
                list_str = ", ".join(str(v) for v in value)
                desc_parts.append(f"&lt;strong&gt;{key}:&lt;/strong&gt; {list_str}")
        
        description = "&lt;br/&gt;".join(desc_parts) if desc_parts else "No details available"
        
        # Parse analyzed_at for pubDate
        try:
            dt = datetime.fromisoformat(analyzed_at.replace("Z", "+00:00"))
            pub_date = format_datetime(dt)
        except (ValueError, AttributeError):
            pub_date = format_datetime(datetime.utcnow())
        
        # Escape the title
        safe_title = self._escape_xml(str(title) if title else "Insight")
        
        return f"""    <item>
      <title>{safe_title}</title>
      <link>{url}</link>
      <description>{description}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{url or f"insight-{raw_item_id}"}</guid>
    </item>"""

    def _generate_rss_feed(
        self, 
        insights: list[Any], 
        raw_store: Any, 
        topic_name: str,
        feed_url: str
    ) -> str:
        """Generate the complete RSS feed XML."""
        now = datetime.utcnow()
        pub_date = format_datetime(now)
        
        # Generate items
        items_xml = "\n".join(
            self._format_rss_item(insight, raw_store) 
            for insight in insights
        )
        
        # Escape topic name for XML
        safe_topic = self._escape_xml(topic_name)
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{safe_topic} 日报</title>
    <link>{feed_url}</link>
    <description>AI/ML研究洞察日报 - {safe_topic}</description>
    <language>zh-CN</language>
    <lastBuildDate>{pub_date}</lastBuildDate>
    <generator>insight-mode RSS Plugin</generator>
    <atom:link href="{feed_url}" rel="self" type="application/rss+xml" />
{items_xml}
  </channel>
</rss>
"""

    def deliver(
        self,
        insight_store: Any,
        config: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Generate RSS feed file from insights."""
        config = config or {}
        context = context or {}
        
        # Get configuration
        output_path = config.get("output_path", "public/rss.xml")
        max_insights = int(config.get("max_insights", 50))
        feed_url = config.get("feed_url", "https://example.com/rss.xml")
        
        # Get topic configuration
        topic_config = context.get("topic") or {}
        topic_name = topic_config.get("name", "洞察")
        
        # Get raw_store from context
        raw_store = context.get("raw_store")
        
        # Get insights
        insights = insight_store.list_since(limit=max_insights)
        if not insights:
            logger.info("RSS plugin: no insights to generate")
            # Still write an empty feed
        
        # Generate RSS feed
        rss_content = self._generate_rss_feed(
            insights, raw_store, topic_name, feed_url
        )
        
        # Ensure output directory exists
        import os
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Write RSS file
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rss_content)
            logger.info("RSS plugin: generated feed at %s with %d items", output_path, len(insights))
            return True
        except Exception as e:
            logger.exception("RSS plugin: failed to write feed: %s", e)
            return False


# Config-driven loading: module exports this instance
plugin = RSSDeliveryPlugin()
