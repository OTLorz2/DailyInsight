"""
Main entry: fetch -> store -> analyze -> delivery (email).
Run daily via cron or Task Scheduler. Config: config.yaml + .env.
"""
import logging
import os
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from dotenv import load_dotenv

from src.storage import RawStore, InsightStore
from src.fetcher import run_fetch
from src.analyzer import run_analyze
from src.delivery.interface import load_plugins_from_config

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_daily")


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    config = load_config()
    storage_cfg = config.get("storage") or {}
    db_path = storage_cfg.get("path", "data/insight.db")
    db_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    raw_store = RawStore(db_path)
    insight_store = InsightStore(db_path)

    # 1) Fetch
    sources_cfg = config.get("sources") or {}
    fetch_counts = run_fetch(raw_store, sources_cfg)
    logger.info("Fetch counts: %s", fetch_counts)

    # 2) Analyze
    analyzer_cfg = config.get("analyzer") or {}
    n_analyzed = run_analyze(
        raw_store,
        insight_store,
        model=analyzer_cfg.get("model"),
        max_items_per_run=analyzer_cfg.get("max_items_per_run", 30),
        summary_max_chars=analyzer_cfg.get("summary_max_chars", 500),
    )
    logger.info("Analyzed %d new items", n_analyzed)

    # 3) Delivery (batch plugins only; current: email)
    delivery_cfg = config.get("delivery") or {}
    plugin_ids = delivery_cfg.get("plugins") or []
    plugins = load_plugins_from_config(plugin_ids)
    context = {"raw_store": raw_store}
    for p in plugins:
        plugin_config = delivery_cfg.get(p.plugin_id) or {}
        ok = p.deliver(insight_store, config=plugin_config, context=context)
        logger.info("Delivery %s: %s", p.plugin_id, "ok" if ok else "failed")

    logger.info("run_daily finished")


if __name__ == "__main__":
    main()
