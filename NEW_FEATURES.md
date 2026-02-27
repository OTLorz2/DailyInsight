# New Features Implementation Summary

This document describes the new features added to insight-mode.

## Overview

Added support for **multiple paper sources** and **multiple delivery channels** to enhance the flexibility and reach of the insight aggregator.

---

## 1. Multiple Source Support

### New Sources Added

#### 1.1 bioRxiv (Biology Preprints)
- **File**: `src/sources/biorxiv.py`
- **API**: https://api.biorxiv.org/
- **Categories**: Biology preprints
- **Config**:
  ```yaml
  sources:
    biorxiv:
      enabled: false
      max_results: 20
  ```

#### 1.2 medRxiv (Medical Preprints)
- **File**: `src/sources/medrxiv.py`
- **API**: https://api.biorxiv.org/ (same as bioRxiv)
- **Categories**: Medical and health sciences preprints
- **Config**:
  ```yaml
  sources:
    medrxiv:
      enabled: false
      max_results: 20
  ```

#### 1.3 Semantic Scholar
- **File**: `src/sources/semantic_scholar.py`
- **API**: https://api.semanticscholar.org/
- **Categories**: Computer Science, Machine Learning, and more
- **Features**:
  - Full-text search with custom queries
  - Field of study filtering
  - Citation count metadata
- **Config**:
  ```yaml
  sources:
    semantic_scholar:
      enabled: false
      categories: ["Computer Science", "Machine Learning"]
      max_results: 20
      query: "machine learning OR artificial intelligence"
  ```
- **Environment Variable**: `SEMANTIC_SCHOLAR_API_KEY` (optional but recommended for higher rate limits)

### Updated Fetcher

The `src/fetcher.py` has been updated to support all new sources:
- Modular source adapter imports
- Independent enable/disable for each source
- Separate error handling per source
- Source-specific configuration support

---

## 2. New Delivery Plugins

### 2.1 Slack Integration
- **File**: `src/delivery/plugins/slack.py`
- **Type**: Incoming Webhook
- **Features**:
  - Rich Block Kit formatting
  - Color-coded sections
  - Automatic truncation for message limits
  - Support for multiple insights per message
- **Setup**:
  1. Create a Slack app at https://api.slack.com/apps
  2. Enable "Incoming Webhooks"
  3. Copy the webhook URL
- **Config**:
  ```yaml
  delivery:
    plugins: [email, slack]
    slack:
      webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
      max_insights: 20
  ```

### 2.2 Discord Integration
- **File**: `src/delivery/plugins/discord.py`
- **Type**: Webhook
- **Features**:
  - Rich embed formatting
  - Color-coded embeds (Discord blurple)
  - Support for up to 10 embeds per message
  - Timestamp and footer metadata
- **Setup**:
  1. In Discord, go to Server Settings -> Integrations
  2. Create a new Webhook
  3. Copy the webhook URL
- **Config**:
  ```yaml
  delivery:
    plugins: [email, discord]
    discord:
      webhook_url: "https://discord.com/api/webhooks/YOUR/WEBHOOK/TOKEN"
      max_insights: 10
  ```

### 2.3 RSS Feed Generation
- **File**: `src/delivery/plugins/rss.py`
- **Type**: File Generation
- **Features**:
  - RSS 2.0 compliant feed
  - Atom link support
  - Configurable output path
  - Support for up to 50 items
- **Usage**:
  - The RSS file can be served by a web server or CDN
  - Can be consumed by RSS readers (Feedly, Inoreader, etc.)
- **Config**:
  ```yaml
  delivery:
    plugins: [email, rss]
    rss:
      output_path: "public/rss.xml"
      feed_url: "https://your-domain.com/rss.xml"
      max_insights: 50
  ```

---

## 3. Configuration Updates

### 3.1 Updated `config.yaml`
- Added new source configurations (biorxiv, medrxiv, semantic_scholar)
- Added new delivery plugin configurations (slack, discord, rss)
- All new sources and plugins are disabled by default for safety

### 3.2 Updated `.env.example`
- Added `SEMANTIC_SCHOLAR_API_KEY`
- Added `SLACK_WEBHOOK_URL`
- Added `DISCORD_WEBHOOK_URL`

---

## 4. Migration Guide

### Adding New Sources

1. **bioRxiv**: Set `sources.biorxiv.enabled: true` in config.yaml
2. **medRxiv**: Set `sources.medrxiv.enabled: true` in config.yaml
3. **Semantic Scholar**: 
   - Set `sources.semantic_scholar.enabled: true`
   - Optionally set `SEMANTIC_SCHOLAR_API_KEY` in .env

### Adding New Delivery Channels

1. **Slack**:
   - Add `slack` to `delivery.plugins` list
   - Set `delivery.slack.webhook_url`
   - Create Slack app and webhook

2. **Discord**:
   - Add `discord` to `delivery.plugins` list
   - Set `delivery.discord.webhook_url`
   - Create Discord webhook

3. **RSS**:
   - Add `rss` to `delivery.plugins` list
   - Set `delivery.rss.output_path`
   - Serve the generated file via web server

---

## 5. Testing

### Manual Testing Commands

```bash
# Test bioRxiv source
python -c "from src.sources.biorxiv import fetch_biorxiv; print(fetch_biorxiv(max_results=5))"

# Test medRxiv source
python -c "from src.sources.medrxiv import fetch_medrxiv; print(fetch_medrxiv(max_results=5))"

# Test Semantic Scholar source
python -c "from src.sources.semantic_scholar import fetch_semantic_scholar; print(fetch_semantic_scholar(max_results=5))"

# Test Slack plugin
python -c "from src.delivery.plugins.slack import SlackDeliveryPlugin; print(SlackDeliveryPlugin().plugin_id)"

# Test Discord plugin
python -c "from src.delivery.plugins.discord import DiscordDeliveryPlugin; print(DiscordDeliveryPlugin().plugin_id)"

# Test RSS plugin
python -c "from src.delivery.plugins.rss import RSSDeliveryPlugin; print(RSSDeliveryPlugin().plugin_id)"
```

---

## 6. Files Changed

### New Files
- `src/sources/biorxiv.py` - bioRxiv source adapter
- `src/sources/medrxiv.py` - medRxiv source adapter
- `src/sources/semantic_scholar.py` - Semantic Scholar source adapter
- `src/delivery/plugins/slack.py` - Slack delivery plugin
- `src/delivery/plugins/discord.py` - Discord delivery plugin
- `src/delivery/plugins/rss.py` - RSS feed generation plugin

### Modified Files
- `src/fetcher.py` - Added support for multiple sources
- `config.yaml` - Added new source and delivery configurations
- `.env.example` - Added new environment variables

---

## 7. Future Enhancements

### Potential Additions
1. **PubMed Integration** - Medical literature from NCBI
2. **Hacker News Integration** - Tech news and discussions
3. **Reddit Integration** - Subreddit monitoring
4. **Twitter/X Integration** - Social media insights
5. **PDF Full-text Analysis** - Download and analyze full PDFs
6. **Insight Rating/Feedback** - Track which insights users find valuable

