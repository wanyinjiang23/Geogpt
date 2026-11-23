# 构造失败案例与回归

以下均是人为构造、实际执行的故障，不是线上用户事故。

| 复现 | 原因定位 | 修复策略 | 回归与实测结果 |
|---|---|---|---|
| 医院附近选址 | 缺少可计算距离 | AMBIGUOUS_DISTANCE，禁止猜500m | test_request_schema::test_clarification；评测case_17，澄清 |
| 距医院0.5公里 | 首数字弱基线会当0.5m | 归一500m后Schema校验 | test_units_and_example；评测case_08，预期字段匹配 |
| hospital.crs=None | 坐标单位无依据 | MISSING_CRS，禁止强赋4326 | test_failure_trace；case_35，FAILED且无虚假结果路径 |
| 栅格仿射偏移5m或分辨率20m | 同下标不代表同地面像元 | 严格拒绝错位，不暗自重采样 | test_raster_alignment两参数均通过 |
| ../secret或C盘路径 | 模型路径越界风险 | 注册ID、safe_path、下载名白名单 | test_traversal五参数；test_web非法下载404 |
| 距医院不超过1m | 合成网格点全部不满足 | empty与validation_error区分 | test_empty；case_33/34，empty且无推荐 |
| 改写导出医院距离或得分 | 报告可能与几何不一致 | 独立重算距离/排名 | test_tampered_results_rejected，拒绝篡改 |
| 模型坏JSON/拒答/长度截断/超时 | 不保证服务商始终按Schema返回 | MODEL_*澄清，无GIS执行 | tests/test_model.py MockTransport通过，非真实模型事件 |

没有将这些案例的通过率描述为线上改善；原版不可运行，无法量化旧版与v2收益。
