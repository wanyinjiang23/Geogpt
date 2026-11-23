# 离线评测实际报告

数据：程序生成的合成场景；模式：规则解析；不代表真实模型或真实城市效果。

命令：`.venv/Scripts/python -m evals.run_eval`

| 指标 | 实测 |
|---|---|
| cases | 44 |
| passed | 44 |
| failed | [] |
| field_accuracy | {"correct": 24, "total": 24, "rate": 1.0} |
| weak_baseline_field_accuracy | {"correct": 14, "total": 24, "rate": 0.5833333333333334} |
| task_success_rate | 1.0 |
| tool_validity | {"valid": 20, "total": 20, "rate": 1.0} |
| constraint_violation | {"violations": 0, "recommended": 56, "rate": 0.0} |
| empty_recognition | {"correct": 2, "total": 2} |
| buffer_500m_area_error_m2 | 78.85066422796808 |
| median_elapsed_s | 0.002187899997807108 |
| api_cost | null |
| model_tokens | null |
| environment | {"python": "3.13.13", "shapely": "2.2.0", "pyproj": "3.8.0", "pydantic": "2.14.2", "rasterio": "1.5.2"} |

字段准确率按已标注顶层字段精确匹配计数（约束列表整体算一个字段），不是逐槽位模型准确率。
工具必要性按用例应执行且白名单工具仅调用一次判断；合法拒绝无工具调用。
弱基线为本轮编写的首数字解析器，仅比较相同文本的已标注字段；不能称为原版对照。
旧版解析/ReAct因TSD文件不可运行；旧版与v2、预检消融、仅地图vs结果校验的完整对照尚未完成。
成本和token未使用API，记为不可用；耗时含文件写入、同机运行，不可推断生产性能。
原始记录：evals/results/records.json；轨迹与工件：evals/results/runs/<run_id>/。
几何容差测试和预检故障注入另见tests；样本为人工构造的小集合，不得外推真实任务成功率。
