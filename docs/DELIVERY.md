# 本轮交付清单

核心结构：原app保留为历史毕业设计；geosite独立包实现Schema/双模式需求解析、确认状态机、统一米制GIS、确定性评分、独立结果/工件验证和本地Web演示。main_web为兼容入口；旧chat现在只解析，执行需确认，原open-folder移除。

## 实际文件清单

- `.env.example`
- `.github/workflows/offline.yml`
- `.gitignore`
- `README.md`
- `app/tool/bufferchain.py`
- `app/tool/get_buff.py`
- `app/tool/gis_tools.py`
- `docs/ARCHITECTURE_DECISIONS.md`
- `docs/BASELINE.md`
- `docs/DELIVERY.md`
- `docs/IMPLEMENTATION_PROGRESS.md`
- `docs/SECURITY_AUDIT.json`
- `docs/VALIDATION_RESULTS.json`
- `docs/career/CONTRIBUTIONS.md`
- `docs/career/DEMO_SCRIPT.md`
- `docs/career/INTERVIEW_QA.md`
- `docs/career/PROBLEM_SOLUTION_RESULT.md`
- `docs/career/RESUME_BULLETS.md`
- `docs/evaluation/BAD_CASES.md`
- `docs/evaluation/REPORT.md`
- `docs/product/PRD.md`
- `docs/product/PRODUCT_METRICS.md`
- `docs/product/USER_FLOW.md`
- `docs/product/WIREFRAMES.md`
- `evals/__init__.py`
- `evals/cases.jsonl`
- `evals/run_eval.py`
- `geosite/__init__.py`
- `geosite/__main__.py`
- `geosite/artifacts.py`
- `geosite/cli.py`
- `geosite/datasets.py`
- `geosite/gis.py`
- `geosite/model.py`
- `geosite/parser.py`
- `geosite/schema.py`
- `geosite/selection.py`
- `geosite/ui.html`
- `geosite/web.py`
- `geosite/workflow.py`
- `main_web.py`
- `pyproject.toml`
- `requirements-lock.txt`
- `setup.py`
- `tests/test_crs_and_geometry.py`
- `tests/test_gis_tools.py`
- `tests/test_model.py`
- `tests/test_request_schema.py`
- `tests/test_security.py`
- `tests/test_site_selection.py`
- `tests/test_web.py`
- `tests/test_workflow.py`

## 验证结果

| 项目 | 结果 | 证据 |
|---|---|---|
| pytest | 46通过/0失败/0跳过；1上游弃用警告 | outputs/pytest.xml |
| 离线评测 | 44通过/0失败；推荐56点违规0 | evals/results/summary.json、records.json |
| 静态检查/格式 | 通过/通过 | ruff check和format --check |
| 安装、依赖 | 可编辑安装成功；pip check通过 | requirements-lock.txt、CLI帮助实际运行 |
| Demo | 完成，144网格/77可行候选/Top-3 | outputs/<run_id>/及浏览器实际点击 |
| 原版 | 退出1，无法形成基线 | BASELINE.md、SECURITY_AUDIT.json |
| 真实模型、远程CI | 未执行 | 仅MockTransport测试，未推送远程 |

最短Demo：`.venv/Scripts/python -m geosite --confirm`。
真实模型（需用户自行配置密钥/模型、允许费用）：`.venv/Scripts/python -m geosite --mode llm --allow-model-api`；先解析待确认，真实网络未验证。
评测：`.venv/Scripts/python -m evals.run_eval`。

问题—原因—解决—效果：0.5公里误读风险通过单位归一测试；缺CRS不再猜测、以MISSING_CRS失败；错位栅格严格拒绝；篡改距离/得分被独立校验拦截。详见career/PROBLEM_SOLUTION_RESULT.md及evaluation/BAD_CASES.md。

产品文档在docs/product，求职证据在docs/career。未完成项、阶段说明、具体后续步骤在IMPLEMENTATION_PROGRESS.md；安全风险在SECURITY_AUDIT.json和README。历史凭证必须在服务商后台轮换/吊销，6个TSD文件不具备完整审查条件。
