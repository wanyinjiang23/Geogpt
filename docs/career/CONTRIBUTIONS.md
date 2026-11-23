# 贡献边界

基准提交7964043。仓库缺少上游出处/许可证/作者变更证据，不能精确划分原作者与OpenManus作者贡献。app/Agent/base.py、react.py及toolcall命名体现原有Agent/ReAct/工具抽象；GIS工具位于app/tool/get_buff.py、gis_tools.py，是本次之前已经存在的毕业设计能力，不算本轮新增。

本轮新增：geosite/schema.py（Schema）；parser.py与model.py（双解析入口）；workflow.py（固定状态机与Trace）；gis.py/datasets.py（有界内核、合成数据）；selection.py（筛选评分与独立验证）；artifacts.py（可复算导出）；web.py/ui.html（轻量界面）；tests和evals；项目与产品文档。修改旧源码只包括可读凭证/路径脱敏、关闭eval、缺CRS拒绝；main_web.py迁移为v2入口。

没有独立研发通用Agent框架、没有真实用户增长、没有商业落地证据。模型模式未实网验证；不宣称模型效果提升。求职者应在面试前亲自复算代码、补充自己的设计与使用证据，准确说明AI辅助开发。
