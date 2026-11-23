# Phase 0 原版与离线基线

基准：分支 main，提交7964043（geogpt_init），审查时只有新增任务书未跟踪，无其他用户改动。任务书原样保留；没有提交、push、远程PR或历史重写。

旧版命令 `.venv/Scripts/python main.py` 实际退出1。`main.py`、`app/llm.py`、`app/schema.py`、`app/Agent/gis_agent.py`、`app/Agent/toolcall.py`、`app/tool/tool_collection.py`共6个文件以%TSD开头，属于不可当普通Python读取的内容，具体加密软件及恢复方法未知。此前初步口头估计7个，以此次脚本审查6个为准。旧Web直接导入这些模块，也不能构成有效基线。**Baseline unavailable**：无法取得旧版解析率、工具轨迹、耗时、成本，禁止填入猜测值。

可读旧GIS工具存在：缓冲/交并差、坡度坡向、栅格运算、绘图；发现缺CRS时直接赋4326、自由表达式eval、个人绝对路径等风险。仅局部安全修订，未声称旧GIS全部修复。新流程独立运行，有意不调用旧工具。

替代基线：`evals/run_eval.py::weak_baseline`为新写的首数字解析器（默认米、医院、within），在相同文本标注字段上评测；它不是旧OpenManus/ReAct。实际结果随评测生成于evaluation/REPORT.md。

离线Demo：`.venv/Scripts/python -m geosite --confirm`实际COMPLETED，产物可读取。环境Python3.13.13，依赖安装版本在requirements-lock.txt；测试结果在outputs/pytest.xml。安全审查的机器记录在SECURITY_AUDIT.json，不含任何密钥正文。
