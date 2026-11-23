"""Unified offline entry point, independent of legacy encrypted source."""

import argparse
import json
import os
from pathlib import Path

from .parser import EXAMPLE
from .workflow import run


def main():
    parser = argparse.ArgumentParser(description="GeoSite Agent v2 · 合成数据离线选址")
    parser.add_argument("--prompt", default=EXAMPLE)
    parser.add_argument("--request", type=Path, help="用户选择的结构化 JSON 文件（不是模型提供的路径）")
    parser.add_argument("--confirm", action="store_true", help="预确认参数并执行；默认只解析")
    parser.add_argument("--mode", choices=["offline", "llm"], default="offline")
    parser.add_argument(
        "--allow-model-api", action="store_true", help="明确允许向配置的服务发送需求并产生API费用"
    )
    parser.add_argument("--output", type=Path, default=Path(os.getenv("GEOSITE_OUTPUT_DIR", "outputs")))
    args = parser.parse_args()
    if args.mode == "llm" and not args.allow_model_api:
        parser.error("LLM模式需显式--allow-model-api；可能产生服务商费用")
    value = json.loads(args.request.read_text(encoding="utf-8")) if args.request else args.prompt
    result = run(value, args.output, confirmed=args.confirm, mode=args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["state"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
