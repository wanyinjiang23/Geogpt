# GeoGPT 本地对话界面

这层 Web 适配器直接调用 `app/Agent/gis_agent.py` 中的 GISAgent，保留原有 Agent、Memory 和 GIS 工具链。原来的 `main.py` 未修改。没有恢复已删除的 geosite / georetail 模块。

在项目目录执行（PowerShell，推荐 Python 3.11–3.13）：

```powershell
cd D:\Geogpt\GeoGPT
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
Copy-Item .env.example .env  # 仅首次配置；已有 .env 时不要覆盖
# 编辑 .env，填写你自己的 GEOGPT_API_KEY
.\.venv\Scripts\python.exe main_web.py
```

如果虚拟环境没有 pip，也可以执行 `uv pip install --python .venv/Scripts/python.exe -r requirements-web.txt`。

浏览器打开 http://127.0.0.1:8000，API 文档在 `/docs`。服务默认仅监听本机，使用单进程运行，不要添加 `--workers`。前端为原生 HTML/CSS/JavaScript，由 FastAPI 同源提供，无需 Node 构建。

支持多轮对话、发送、Enter 发送 / Shift+Enter 换行、执行进度、新建对话、暂停 / 停止。刷新页面可以恢复当前浏览器标签的对话。会话保存在服务内存，重启后清空。

“暂停 / 停止”会终止本次任务的独立进程，不提供从断点恢复；之后可继续发送新消息，保留之前完成轮次的 Agent 记忆。已写入磁盘的 GIS 结果不会回滚。每次任务最长 15 分钟。

将原始数据放入项目 `data` 目录，并在消息中说明数据名称、分析方式和输出位置。知识库检索工具 QAchain 还需要 `GEOGPT_KNOWLEDGE_FILE` 和支持其嵌入请求的 API 配置；这沿用原工具的逻辑。

后端未配置或缺少依赖时页面会显示具体提示，不会生成模拟回复。密钥只在服务端 `.env` 中配置，不会传到浏览器。原 `main.py` 当前带有二进制文件头，不属于可执行的普通 Python 源码；Web 入口直接调用可读取的 GISAgent，不改写该文件。

验证命令：`uv pip install --python .venv/Scripts/python.exe pytest httpx`，然后 `.\.venv\Scripts\python.exe -m pytest web_tests -q`。测试使用受控模型响应验证原 GISAgent 与工具链，避免产生真实模型费用。
