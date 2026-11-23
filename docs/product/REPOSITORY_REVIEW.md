# 仓库审查与复用决策

审查日期：2026-11-09。开始前工作区已有多处修改及未跟踪文件，本次未重置、提交或覆盖其内容。

| 现有模块 | 观察 | 本次处理 |
| --- | --- | --- |
| app/Agent | Base/ReAct/ToolCall/GISAgent 原始机制，部分依赖不可直接导入 | 保留；未迁移新框架，零售另用有限工作流 |
| app/tool/base.py | BaseTool/Pydantic及ToolResult合同 | 新RetailAnalysisTool、RetailGISTool直接继承复用 |
| app/tool/__init__.py | 导入基类会连带导入ToolCollection等TSD模块 | 惰性导入公共类，避免污染轻量合同；增加回归测试 |
| app/tool/gis_tools.py | 重依赖GIS/LangChain混合工具 | 保留；未安装整套遗留依赖，未宣称旧main.py已恢复 |
| geosite/gis.py | 已有米制CRS、Layer、buffer、overlay、栅格及路径边界 | 直接复用；buffer/overlay增加可选target，默认行为不变 |
| geosite/workflow.py | 已有有限状态与用户确认、轨迹机制 | 复用设计模式，新增两次确认的经营工作流 |
| geosite/model.py | HTTP JSON参数解析及安全异常 | 参考其边界；零售解析使用专属Schema，不复用公共设施语义 |
| geosite/web.py / main_web.py | 公共服务设施选址原演示入口 | 保留原行为；新增Streamlit独立入口 |
| inputdata/data | 来源及许可未知 | 不读取、不上传，生成CoffeeLab独立演示数据 |
| pyproject / tests | 既有v2环境和测试 | 增加retail可选依赖和零售测试，回归原测试 |

安装环境：现有 D:/Geogpt/GeoGPT/.venv，使用uv新增pandas、streamlit、folium、streamlit-folium；未替换既有虚拟环境。初次默认uv缓存目录不可写，改为过程目录；网络访问需要环境审批，审批通过后完成安装。

凭证：既有README记载Git历史曾暴露凭证；本次未加载任何旧凭证。所有新增API配置只读环境变量。应在服务商后台吊销/轮换原凭证；本次不重写Git历史或扫描并输出密钥。此审查不是全仓库安全认证。

改动理由：避免不必要的框架迁移和旧工具重写；使业务计算、确认边界和GIS可独立测试。局限：原TSD内容不可审查，旧main.py及所有原GIS工具没有做全量恢复。真实经营/公开GIS和在线模型接入均未实网验收。
