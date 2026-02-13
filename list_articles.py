"""
查看 fetcher 抓取下来的 arXiv 文章。
用法: python list_articles.py [--limit N] [--since ISO日期]
默认数据库: config.yaml 中的 storage.path，缺省为 data/insight.db
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from src.storage import RawStore


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="查看已抓取的 arXiv 文章")
    p.add_argument("--limit", type=int, default=50, help="最多显示条数，默认 50")
    p.add_argument("--since", type=str, default=None, help="只显示此时间之后抓取的 (ISO 格式，如 2025-02-01)")
    p.add_argument("--db", type=str, default=None, help="指定数据库路径，默认用 config.yaml")
    args = p.parse_args()

    config = load_config()
    storage_cfg = config.get("storage") or {}
    db_path = args.db or storage_cfg.get("path", "data/insight.db")
    db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        print(f"数据库不存在: {db_path}")
        print("请先运行 python run_daily.py 进行抓取。")
        sys.exit(1)

    raw_store = RawStore(db_path)
    items = raw_store.list_since(since_iso=args.since, limit=args.limit)

    print(f"共 {len(items)} 条 (数据库: {db_path})\n")
    for i, it in enumerate(items, 1):
        print(f"--- [{i}] id={it.id} | {it.fetched_at} | {it.source} ---")
        print(f"标题: {it.title}")
        print(f"链接: {it.url}")
        summary_preview = (it.summary or "")[:200].replace("\n", " ")
        if len(it.summary or "") > 200:
            summary_preview += "..."
        print(f"摘要: {summary_preview}")
        print()


if __name__ == "__main__":
    main()
