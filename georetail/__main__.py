import argparse
from pathlib import Path
from .data import generate
from .parser import DEMO_PROMPT
from .schema import Strategy
from .workflow import RetailWorkflow

parser = argparse.ArgumentParser(description="CoffeeLab 离线模拟 Demo")
parser.add_argument("--confirm-demo", action="store_true", help="预确认演示指标和演示策略，仅用于合成数据自动验收")
parser.add_argument("--output", type=Path, default=Path("../过程文件/GeoRetail_20261109/runs"))
args = parser.parse_args()
flow = RetailWorkflow(generate()).prepare(DEMO_PROMPT)
if args.confirm_demo:
    flow.diagnose(confirmed=True).screen(Strategy().model_dump(), confirmed=True)
print(flow.state)
print(flow.save(args.output))
if flow.state == "FAILED":
    raise SystemExit(1)
