# 实施进度（2026-10-30，Asia/Shanghai）

本轮交付可运行的GeoSite v2合成原型，未将全部任务书验收项标为完成。工作区保留，未提交/推送/部署公网/创建远程PR/调用收费模型。

| 阶段 | 实际完成 | 遗留与验证边界 |
|---|---|---|
| Phase 0 | main/7964043状态记录；可读源码凭证脱敏、环境配置、个人路径移除；独立venv、锁定依赖、CLI/Web入口、旧版基线失败记录 | 6个TSD文件内容不可审查/不可运行；历史凭证仍须轮换；未核实上游许可证；旧功能整体兼容性未验收 |
| Phase 1 | 米制CRS、统一对齐、缺CRS拒绝、无效/空几何拒绝、去重、注册ID/路径边界、栅格严格对齐/NoData、结构化选择工具结果 | 原GIS工具未整体适配统一协议；栅格不自动重采样、不接受表达式；尚无广域CRS选择器 |
| Phase 2 | 规则解析、单位归一、硬软分离、确认门、固定状态机、单工具白名单计划；可选真实模型Schema适配器与MockTransport测试 | 真实模型未实网验证；语义准确性不能由Mock证明；无动态规划、取消、持久恢复；中文距离数字未支持 |
| Phase 3 | 250m网格筛选、独立约束/距离/分数校验、分项解释、偏好重算、SVG地图、GeoJSON/CSV/JSON/MD/Trace | 单约束是网格候选，不是真实POI；空网格不等于连续无解；无真实业务权重依据 |
| Phase 4 | 四区域本地UI、确认、错误/空态与重试、PRD/流程/原型/指标文档；桌面浏览器实际点击验证 | 参数仍用JSON编辑；没有真实用户可用性研究、实时进度推送、移动端专项测试 |
| Phase 5 | 44条构造案例；机器计算指标、报告、原始运行Trace、弱解析基线、8类构造Bad Case | 不是原版对照；原ReAct/预检/仅地图完整消融未完成；不是逐槽位或真实模型评测 |
| Phase 6 | README、安装验证、46项pytest、ruff、CI配置、贡献边界、问答/简历/演示脚本 | Linux/远程CI未执行；许可证/真实数据授权待核实；不声称上线或产品效果 |

## 实际命令与结果

- `.venv/Scripts/python -m pip install --no-deps --no-build-isolation -e .`：成功安装geosite-agent 2.0.0。
- `.venv/Scripts/geosite --help`：退出0；终端编码可能影响中文显示，文件内容为UTF-8。
- `.venv/Scripts/python -m geosite --confirm`：COMPLETED；默认144个网格中心、77个满足条件、Top-3；每次独立run_id。
- `.venv/Scripts/python -m pytest -q --junitxml=outputs/pytest.xml`：46 passed，0 failed，0 skipped；1条Starlette/httpx弃用警告，没有隐藏该警告。
- `.venv/Scripts/python -m ruff check geosite tests evals`：通过；format --check：22个Python文件通过。
- `.venv/Scripts/python -m evals.run_eval`：44/44断言通过；56个Top-K违规0；空结果2/2；标注顶层字段24/24；新弱基线14/24，不是原版性能提升。
- `.venv/Scripts/python -m pip check`：No broken requirements found。
- `git diff --check`：初次发现旧模块新增行尾空格，已清理，再检退出0。
- `.venv/Scripts/python main.py`：原版实际退出1，TSD源文件；记录为Baseline unavailable。

pytest初轮39项通过后增加7项模型协议测试，最终46项。初轮Shapely弃用警告通过新transform接口修正；最终仍有1项上游TestClient弃用警告。早期一次读取Demo输出用了错误UTF-16编码，已确认PowerShell输出实际UTF-8；Demo本身当时已COMPLETED。

## 下一步（按业务价值排序）

1. 用户在服务商后台吊销/轮换历史凭证，核实原始源码与数据发布授权，取得6个TSD文件合法明文副本。
2. 用明确模型与允许的API预算执行固定真实模型评测；保留usage/模型版本/温度与费用，加入逐槽位标注。
3. 接入一套有许可和CRS依据的城市边界/设施数据，实现真实POI单约束查询与数据目录UI；对照独立GIS软件复核。
4. 将JSON编辑改成字段表单，做真实目标用户可用性测试；再评估长任务取消/进度和恢复。
5. 恢复旧版后固定输入、预算、数据和模型做ReAct/预检/结果校验消融；没有证据前不写收益百分比。
