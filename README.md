# GeoRetail Agent · CoffeeLab

基于 GeoGPT/GeoSite 的连锁咖啡经营分析与拓店初筛作品集 MVP。中文五页交互原型与后端共用一条流程：自然语言 → 指标确认 → 经营排名/特征比较 → 策略确认 → GIS候选 → 地图与报告。

全部经营、门店、候选和POI均为固定种子的**模拟数据**，不是任何真实品牌内部系统，不预测新店收益，不代替实地尽调。原 GeoSite v2 仍保留，原说明见 [旧版 README](docs/legacy/README_GEOSITE_V2.md)。原 main.py 的TSD及依赖限制没有整体修复。

## 环境（Windows PowerShell）

```powershell
cd D:\Geogpt\GeoGPT
# 当前机器已存在该环境，无需重建。新机器首次执行：
uv venv .venv --python 3.13
# 建议使用项目兼容依赖；所有包都装入指定环境
uv --cache-dir D:\Geogpt\过程文件\GeoRetail_20261109\uv-cache pip install --python .venv/Scripts/python.exe -e ".[retail,dev]"
```

需要 uv 和 Python 3.11+，本机实测3.13.13。`requirements-retail-lock.txt`记录本机实际环境；要复现本轮版本，可使用 `uv pip install --python .venv/Scripts/python.exe -r requirements-retail-lock.txt`。其中包括原GeoSite所需GIS/Web依赖，没有安装遗留app所有LangChain重依赖。

## 启动五页原型

```powershell
.venv/Scripts/python -m streamlit run ui/retail_app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

打开 [本地工作台](http://127.0.0.1:8501)。也可以执行 `./start_retail.ps1`。左侧可切换经营分析总览、门店经营诊断、拓店策略、候选商圈、分析记录与报告。

默认问题：“分析最近六个月利润率最高的成熟门店有什么共同特点，然后参考这些特点，在目标城市筛选三个值得进一步考察的候选商圈。”

点击解析需求 → 进入诊断 → 勾选指标确认并执行 → 制定策略 → 修改约束和权重并确认 → 查看候选地图/详情 → 报告导出。具体交互和异常演示见 [原型指南](docs/prototype/PROTOTYPE_GUIDE.md)。总览时间控件只调整总览；分析窗口由问题解析后在诊断页确认。

## 数据与无界面演示

```powershell
.venv/Scripts/python scripts/generate_retail_data.py
.venv/Scripts/python -m georetail --confirm-demo
```

生成50家CoffeeLab门店、覆盖2025年12个自然月的经营记录（开业前无记录）、24个候选点和220个POI。种子42；默认运行实时重新生成同一份数据，CSV导出用于复核，当前不提供用户文件导入。`--confirm-demo`仅用于预确认合成演示指标/策略的自动验收；不加时只解析并等待确认。

执行产物独立保存在 `D:/Geogpt/过程文件/GeoRetail_20261109/`：demo_data为数据导出，runs/任务ID为报告/候选CSV/trace，pytest.xml为测试证据，流程图SVG与阶段记录也在其中。源代码、产品文档和测试保存在仓库，环境在GeoGPT/.venv。

## 离线与在线模式

离线默认：有限中文语法与确定性状态机，**不是LLM自主决策**。支持最近1—12个月、利润率/营业额/利润/订单/前期增长率、成熟门店及前N家。缺时间/指标或未知条件会要求澄清。所有精确财务、统计和空间数值由Pandas及已有GIS工具计算。

在线可选：兼容Chat Completions JSON mode的HTTP服务只解析AnalysisRequest；人工确认、确定性工具与结果验证完全相同。仅MockTransport测试，未调用真实模型，不保证任意服务商兼容。设置 `GEORETAIL_API_KEY`、`GEORETAIL_MODEL`、可选 `GEORETAIL_API_BASE`（默认https://api.openai.com/v1），重启应用后选择在线模式。变量清单见.env.example，程序不自动读取.env。不要把密钥写入源码或提交。在线提交只发送问题文本，仍可能付费；失败显示错误，可手动切离线。

协议依据：[OpenAI JSON mode](https://developers.openai.com/api/docs/guides/structured-outputs#json-mode)。JSON只保证语法，本地Pydantic进一步验证字段，模型不能授予确认或提供计算结果。输出不完整/模型错误/超时均停止。

地图：默认无底图；Leaflet组件首次加载需联网获取CDN资源。勾选公开底图才访问OSM。无网络时可用候选下拉、本地坐标散点与指标表；分析/报告不依赖外部GIS服务。

## 测试

```powershell
.venv/Scripts/python -m pytest -q --junitxml=D:/Geogpt/过程文件/GeoRetail_20261109/pytest.xml
```

[测试报告](docs/evaluation/TEST_REPORT.md)记录实际结果与浏览器检查边界。自动测试覆盖财务公式、排名/筛选、分组/关联、独立GIS约束、Schema、工具异常、确认状态、五页AppTest与核心端到端；原有GeoSite测试同时回归。

## 产品与工程文档

- [完整中文PRD](docs/product/GeoRetail_PRD.md)：用户故事、P0需求、数据模型、Agent边界、指标及验收。
- [业务流程](docs/flows/business_flow.md)与[技术工作流](docs/flows/agent_workflow.md)：Mermaid源与回退路径。
- [仓库审查](docs/product/REPOSITORY_REVIEW.md)：复用和兼容改动理由。
- [五页原型与完整演示指南](docs/prototype/PROTOTYPE_GUIDE.md)。

新增georetail/包含数据、Schema、解析、经营、GIS、BaseTool适配器、状态机及CLI；ui/retail_app.py为共用前端。复用app.tool.BaseTool/ToolResult与geosite.gis，未引入新Agent框架。旧GeoSite CLI可继续使用 `.venv/Scripts/python -m geosite --confirm`，旧Web入口为main_web:app。

## 数据限制与后续

办公商圈模拟利润率增加0.06为人为设定，不是行业发现；历史特征为模拟快照，与候选GIS设施层不同。成熟门店在窗口起点满12个月；只计算完整窗口。增长率为同店等长前期环比，没有2024年数据不能计算同比。候选为有限点集，直线距离/圆形覆盖不能替代路网。缺少真实客流、租金、权属、许可；评分只是人工规则偏好。

仓库历史曾含凭证特征，应在服务商后台轮换或吊销原密钥，本轮未使用这些凭证、不重写历史。inputdata/data来源许可未核验，未读取上传。没有整体LICENSE授权确认，不擅自声明原项目/上游开源许可。当前仅本机单用户演示，真实数据接入、跨重启历史列表、任意自然语言规划、SQL工具、路网和在线模型实测均待后续完成。
