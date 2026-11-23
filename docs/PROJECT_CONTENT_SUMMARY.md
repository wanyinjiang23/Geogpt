# 项目现有内容与功能总览

核对日期：2026-11-05（Asia/Shanghai）。根目录：D:/Geogpt/GeoGPT。

本表依据当前源码、AST结构、目录文件和已有报告，不把任务书或优化建议当实现。对6个TSD文件只确认文件存在与不可普通执行，不猜测内部内容。旧GIS代码只做能力盘点，不宣称端到端已验证。本轮只新增本文并运行本地测试/离线演示，没有修改业务代码或调用外部模型。

本轮实际验证：pytest **46通过、0失败、1条上游弃用警告**；ruff通过；未确认默认需求返回NEEDS_CLARIFICATION，确认后144点→77点→Top-3，COMPLETED。44条评测结果来自现有报告，**未在本轮重跑**。

可以准确概括项目为：保留原GeoGPT毕业设计资产，新增一条经过合成数据验证、可确认参数、可复算空间约束与评分、可导出和追踪的选址初筛流程。

## 一、项目整体组成

| 内容/模块 | 实现的功能 | 解决的问题 | 实现位置 | 当前状态与边界 |
|---|---|---|---|---|
| GeoSite v2主流程 | 自然语言→参数确认→GIS筛选→评分→校验→地图和导出 | 把空间初筛任务连成可演示闭环 | geosite/ | 已通过合成演示；不是生产级城市选址系统 |
| 原GeoGPT毕业设计 | 保留Agent/ReAct结构及15类GIS工具代码 | 保留原项目功能来源与演进依据 | app/、main.py | 6个TSD文件不可当普通Python执行，旧版整体不可运行 |
| 本地Web入口 | 启动FastAPI界面与API | 无需直接修改Python即可演示 | main_web.py、geosite/web.py、ui.html | 接口测试通过；本轮未重新操作浏览器，已有此前目检记录 |
| CLI入口 | 帮助、文本/JSON输入、确认、双解析模式、输出位置 | 安装后有统一可复现入口 | geosite/cli.py、__main__.py | 离线可运行；真实模型需要配置并显式允许API |
| 原始数据与历史结果 | 保留矢量/栅格输入及旧分析产物 | 保留毕业设计分析材料 | inputdata/、data/ | 仅盘点文件，没有接入v2或核实业务真实性与许可 |
| 工程验证 | pytest、ruff、依赖锁定与CI配置 | 降低回归风险并提供复现依据 | tests/、pyproject.toml、.github/ | 本地46测试通过；远程CI未执行 |
| 产品与职业材料 | PRD、流程、指标、架构、评测、面试与简历材料 | 解释实现、取舍及贡献边界 | docs/ | 本轮新增汇总前18份文件：16份MD、2份JSON |

## 二、需求理解与参数治理

| 内容/模块 | 实现的功能 | 解决的问题 | 实现位置 | 当前状态与边界 |
|---|---|---|---|---|
| 离线规则解析 | 识别医院/风险点/道路的明确距离条件和靠近偏好 | 无API也能把限定语法变成请求 | geosite/parser.py | 已测；不是开放领域自然语言理解 |
| 硬约束/软偏好分离 | Constraint控制筛选，Preference控制排序 | 避免用高得分抵消违反硬约束 | geosite/schema.py、selection.py | 已实现；当前操作符仅within/outside |
| 单位归一 | 米、公里、千米统一为米 | 避免0.5公里被误当0.5米 | geosite/parser.py | 单位用例通过；中文距离数字未支持 |
| 结构化请求 | 区域、目标、条件、偏好、Top-K、确认标记 | 让参数可以验证、保存和复算 | SiteSelectionRequest | 区域与图层为限定枚举 |
| 数值与字段验证 | 距离(0,10000]m、Top-K1—20、权重0—100、拒绝额外字段/NaN/Inf | 阻止非法数值和任意扩展参数进入GIS | geosite/schema.py | 已测；不是所有业务约束的验证器 |
| 冲突与权重检查 | 同层上下界冲突、重复偏好、偏好总权重为零时拒绝 | 避免无法解释的输入或除零评分 | SiteSelectionRequest.consistent | 已测；不提前求解全部空间无解情况 |
| 缺项与歧义反馈 | 附近、未知地名/图层、未支持条件进入澄清 | 防止静默猜距离或丢弃条件 | geosite/parser.py、workflow.py | 已测；当前没有多轮补槽对话 |
| 用户确认门 | 默认解析后等待确认，CLI允许预确认，Web勾选执行 | 防止误解参数后立即计算 | geosite/workflow.py、ui.html | 已测；确认与缺信息共用NEEDS_CLARIFICATION状态 |
| 真实模型解析适配 | JSON Schema输出、本地Pydantic验证，输出不直接操作GIS | 把模型理解限制在结构化参数边界 | geosite/model.py | 仅模拟传输测试通过，实网与语义效果未验证 |
| 模型异常处理 | 拒答、截断、非法JSON、超时进入安全澄清；强制清除模型确认权 | 避免把模型异常结果当有效请求 | geosite/model.py、tests/test_model.py | 已通过MockTransport；不是实测模型成功率 |

## 三、GIS数据预检与计算内核

| 内容/模块 | 实现的功能 | 解决的问题 | 实现位置 | 当前状态与边界 |
|---|---|---|---|---|
| 合成数据场景 | 3km×3km区域、2医院点、1风险点、1条道路 | 不依赖原私有数据也能复现演示 | geosite/datasets.py | 人工场景，CRS依据明确为EPSG:32650 |
| 统一分析CRS | 全部图层投影至同一明确米制坐标系 | 避免各层各用一个投影后直接计算 | Layer.aligned | 混合CRS对齐测试通过；不等于自动全球投影选择 |
| 缺CRS与非米制拒绝 | 缺源CRS报错；分析CRS必须投影且轴单位米 | 避免凭空赋4326或把经纬度当米 | geosite/gis.py | 已测 |
| 几何质量检查 | 拒绝None、空几何、无效几何和空图层，检查投影结果有限 | 避免无效空间对象参与运算 | Layer.aligned | 已测；不自动修复无效几何 |
| 几何去重 | 按投影后WKB去掉完全相同几何 | 减少完全重复对象 | Layer.aligned | 已有实现；不是基于名称/地址的实体去重 |
| 数据集注册器 | ID映射受控GeoJSON路径，检查文件、字段、大小和CRS | 避免模型直接拼磁盘路径 | DatasetRegistry | 异常用例已测；未接入默认Web数据导入 |
| 资源边界 | 单层最多10000要素、注册文件最多10MB、栅格最多100万像元、局部区域尺寸限制 | 限制过大输入的资源消耗 | geosite/gis.py、selection.py | 有界演示，未做生产并发/硬超时治理 |
| 米制缓冲 | 融合输入几何后生成指定距离缓冲多边形 | 实现距离覆盖范围 | geosite/gis.py::buffer | 500m几何面积/边界测试通过；圆形用多边形近似 |
| 交集/并集/差集 | 对齐CRS后进行空间叠置 | 组合覆盖和排除区域 | geosite/gis.py::overlay | 3种运算与几何基准测试通过；不是独立软件交叉认证 |
| 栅格对齐校验与求和 | 检查CRS、仿射变换、宽高一致后做掩膜求和 | 避免错位/不同分辨率按数组下标直接相加 | geosite/gis.py::raster_sum | 已测；内核函数未接入选址主流程，不自动重采样 |
| NoData传播 | 任一输入像元无效则结果继续掩膜 | 避免NoData当正常数值参与计算 | raster_sum | 已测；当前只有固定求和，不是通用栅格表达式引擎 |

## 四、选址筛选、排序与解释

| 内容/模块 | 实现的功能 | 解决的问题 | 实现位置 | 当前状态与边界 |
|---|---|---|---|---|
| 候选生成 | 在区域内按250m间距生成网格中心 | 提供可重复且成本有限的候选集合 | geosite/selection.py::select | 默认144点；不代表真实POI或可建设地块 |
| 硬约束筛选 | 逐点算到设施最近距离，判断不超过/至少 | 确保推荐满足明确距离条件 | select | 精确点到几何距离判定；不是路网出行距离 |
| 可行区/排除区 | 研究区域与缓冲区交集/差集 | 在地图上解释筛选空间范围 | select | 边界用缓冲近似，与精确点谓词存在边界容差差异 |
| 加权评分 | 每项1/(1+d/1000)，权重按总和归一 | 提供可复算的偏好排序 | rank_candidates | 原始距离/分项/权重/总分完整；1000m为演示尺度 |
| Top-K与同分顺序 | 按得分降序、候选ID打破平分 | 输出稳定且可重现的推荐列表 | rank_candidates、workflow.py | 默认Top-3；无偏好时得分全零，不代表最优 |
| 修改偏好重算 | 改变偏好及权重后重新执行排序 | 支持用户比较不同偏好方案 | rank_candidates、UI | 回归测试验证排序改变；Web会重跑全流程，没有GIS缓存 |
| 数值与约束复核 | 重算候选距离、边界覆盖、硬约束、排名和分数 | 发现被篡改的指标/得分或违规候选 | validate_results | 篡改测试通过；复核仍使用同一几何库和评分函数 |
| 输出工件复核 | 检查导出文件存在/非空，重读candidates.json并比较 | 避免只返回一个不存在的“成功路径” | geosite/workflow.py | 已测；不是所有格式的外部软件兼容性验证 |
| 空结果区分 | 网格没有符合候选时返回empty，错误返回失败状态 | 避免错误或空结果伪装成正常推荐 | workflow.py | 已测；没有进一步区分连续无解与采样未命中 |
| 推荐解释 | 展示每点距离、阈值、passed、分项得分、权重和总分 | 用户能够核对推荐依据 | selection.py、artifacts.py、UI | 使用实际GIS数值；未做推荐空间多样性/联合设施覆盖优化 |

## 五、受控执行、安全与观测

| 内容/模块 | 实现的功能 | 解决的问题 | 实现位置 | 当前状态与边界 |
|---|---|---|---|---|
| 状态机 | RECEIVED→PARSED→CONFIRMED→DATA_VALIDATED→PLANNED→EXECUTING→RESULT_VALIDATED→COMPLETED | 控制正常阶段顺序 | geosite/workflow.py | 正常路径跳步检查已测；澄清/失败为分支 |
| 固定计划 | 合法请求执行一次site_selection | 限制演示执行链复杂度和重复调用 | workflow.py | 当前没有LLM动态选择工具、ReAct循环或多Agent |
| 运行隔离 | 每次UUID run_id和独立输出目录 | 防止不同任务互相覆盖 | workflow.py | 已测；重试产生新任务，不能断点续跑 |
| 执行轨迹 | 记录状态、耗时、解析参数、图层计数、工具名、产物摘要和错误码 | 定位问题发生在哪个阶段 | trace.json | 不保存原始文本；不等同于任意元数据都已完整脱敏 |
| 统一结果协议 | status、tool_name、run_id、artifacts、metrics、metadata、warnings、error | 工具输出可由程序判断 | geosite/schema.py::ToolResult | 用于v2选择工具；旧版15工具未整体迁移该协议 |
| 路径与下载边界 | 拒绝绝对路径/穿越/越界解析；下载限定UUID与文件名白名单 | 降低任意文件读取风险 | safe_path、web.py | 已测；本地演示无鉴权，UUID不等于访问权限 |
| 输入指令过滤 | 限定长度，拒绝部分命令/路径/提示注入词 | 阻止明显不相关输入进入演示解析 | parser.py、model.py | 有限规则；不能宣称全面防提示注入 |
| 表达式与命令治理 | 禁用旧栅格eval；新内核不接收表达式；新Web移除open-folder | 减少任意代码/系统命令执行入口 | 旧gis_tools.py、geosite/gis.py、main_web.py | 旧代码只做局部治理，未完成整体安全审查 |
| HTML文本转义 | 报告内容转义；UI动态文本用textContent | 避免把属性或错误直接作为HTML注入 | geosite/artifacts.py、ui.html | 已有实现；不是全面Web渗透测试 |
| 配置与凭证 | 可读旧源码改环境变量，提供.env.example并忽略敏感文件 | 避免继续把明文凭证写入源码 | app/tool/、.env.example、.gitignore | 历史仍有凭证特征；轮换状态未知，TSD内部未审查 |

## 六、界面、API与输出物

| 内容 | 已实现功能/信息 | 解决的问题 | 当前边界 |
|---|---|---|---|
| 输入区 | 文本、数据说明、单约束与澄清示例 | 帮助用户开始一次任务 | 限定合成区域 |
| 确认区 | 编辑JSON、勾选、确认执行和重新排序 | 在计算前核对条件 | 尚无业务字段表单 |
| 执行区 | 执行中禁用按钮、状态和可展开Trace | 避免重复点击，展示执行过程 | 同步请求完成后展示，没有实时阶段推送 |
| 结果区 | Top-K、距离、分项得分、约束、地图和下载链接 | 支撑结果解释和复核 | 桌面演示，无用户研究 |
| 状态反馈 | 等待、澄清、非法参数、失败、empty和重试提示 | 避免只显示Python异常 | 重试是新run_id |
| GET / | 返回当前v2页面 | 统一Web入口 | 旧static/index.html没有被当前首页使用 |
| POST /api/parse | 解析并返回待确认请求 | 解耦解析与执行 | Web当前只用规则解析 |
| POST /api/run | 验证结构化请求并执行 | 让页面可以调用核心流程 | 请求需确认；无任务队列 |
| GET /api/artifacts/{run_id}/{name} | 读取白名单工件 | 安全提供结果文件 | 无多用户权限管理 |
| POST /chat、GET /list_data_files | 保留response封装、列出4个合成数据ID | 部分兼容旧接口与数据说明 | chat现在先解析确认，不等同旧Agent行为 |
| map.html | 离线SVG地图、图例、说明 | 无需在线底图也能查看结果 | 无底图和地图平移缩放 |
| map.geojson | 研究区/设施/可行区/排除区/全部候选，坐标转换WGS84 | 方便GIS软件进一步使用 | 含全部候选与Top-K标记，不只是前三点 |
| ranking.csv | 全部候选排名、投影坐标、总分和3类距离 | 便于表格分析 | 完整分项/权重在candidates.json中 |
| candidates.json | 全部候选、投影坐标、原始距离、约束和评分分项 | 支持程序复算和深度解释 | 坐标为分析CRS，需结合元数据 |
| report.md | Top-K数值解释、评分方法、采样和业务限制 | 形成可阅读的结果报告 | 不由模型自由生成空间数值 |
| result.json | 工具状态、指标、工件、CRS和警告 | 程序读取运行结果 | 解析待确认时不保证有结果文件 |
| trace.json | run_id与各阶段事件 | 定位执行和异常 | 不能恢复内存中的中间状态 |

## 七、原版GIS工具逐项盘点

| 旧工具类 | 保留的代码能力 | 原本解决的问题 | 现在是否可算已验证 |
|---|---|---|---|
| QAchainTool | 检索问答/RAG式链代码 | 尝试回答地理知识问题 | 有旧链代码，知识源与效果未验证 |
| CreateBufferTool | 矢量缓冲 | 得到设施周边范围 | 原工具接口未整体实测 |
| IntersectionAnalysisTool | 交集 | 提取共同满足的空间部分 | 原工具接口未整体实测 |
| UnionAnalysisTool | 并集 | 合并多个覆盖区域 | 原工具接口未整体实测 |
| DifferenceAnalysisTool | 差集 | 从区域中排除不符合部分 | 原工具接口未整体实测 |
| DrawMapTool | 矢量地图绘制 | 展示空间结果 | 原工具接口未整体实测 |
| QuerybufferTool | 关键词/距离关联查询 | 查询缓冲范围中的目标 | 旧链依赖与字段/数据兼容未验证 |
| CalculateSlopeTool | DEM坡度计算 | 构造地形坡度指标 | 算法代码存在，未纳入v2验收 |
| CalculateAspectTool | DEM坡向计算 | 构造地形朝向指标 | 算法代码存在，未纳入v2验收 |
| TiffyVisualizeTool | 栅格可视化 | 展示栅格结果 | 旧代码未实测 |
| TiffOverlayTool | 栅格表达式叠加入口 | 原设计支持栅格数学运算 | 原eval已禁用，不能列为当前可用表达式能力 |
| DistanceAnalysis | 距离分析/距离栅格相关逻辑 | 构建到设施距离指标 | 旧算法未整体实测 |
| Reclassification | 栅格重分类 | 将连续值转成等级 | 旧算法未整体实测 |
| WeightedOverlay | 多栅格加权叠加 | 组合多个栅格指标 | 旧算法未整体实测，不等于v2网格点评分 |
| Clip | 按边界裁剪栅格 | 限制分析范围 | 旧算法未整体实测 |

## 八、原版框架、辅助代码与数据资产

| 内容 | 保留内容与用途 | 状态 |
|---|---|---|
| app/Agent/base.py | 基础状态、消息/记忆接口、执行循环与卡住处理 | 可读源码；依赖的原Schema受TSD阻断 |
| app/Agent/react.py | think/act/step抽象 | 可读源码，不能据此宣称旧ReAct端到端可运行 |
| 原main.py、llm.py、schema.py、gis_agent.py、toolcall.py、tool_collection.py | 原入口、模型/请求、GISAgent、工具调用与集合相关文件 | 6个文件有%TSD头；内部功能不可确认 |
| app/tool/base.py | 原BaseTool与ToolResult等结果抽象 | 保留，不等同新schema.ToolResult |
| app/tool/create_chat_completion.py | 从类型构建Schema及聊天调用封装 | 可读代码，依赖原模型模块，未验证 |
| app/tool/terminate.py、app/exceptions.py | 终止工具、工具/Agent/token异常类型 | 保留，原链路未运行 |
| app/tool/get_buff.py | 缓冲、UTM处理、交并差、名称查询、缓冲范围查询辅助函数 | 可读保留；只局部安全修订 |
| app/tool/bufferchain.py | 旧自然语言缓冲查询链 | 保留，不是新规则解析器，未实测 |
| app/prompt/gis.py、toolcall.py | 旧GIS任务与工具调用Prompt | 保留，不证明模型效果 |
| inheritance_diagram | Graphviz继承关系图源码 | 说明旧Agent类关系，不是运行模块 |
| static/ | 旧index.html和2张角色图标，共3文件 | 保留；v2使用geosite/ui.html，当前不挂载该旧目录 |
| inputdata/ | 88文件：12组SHP（1边界+11类设施/POI名称）及3个TIF和配套文件 | 来源/授权/质量未核实；未用于本次v2演示 |
| SHP名称 | bank、entertainment、hospital、hotel、JZboundary、packagestation、residential、restaurant、scenic、school、supermarket、traffic | 名称只表示原文件类别，不证明真实数据内容/时效 |
| TIF名称 | JZDEM、JZlandcover、JZNDVI | 文件名提示高程/土地覆盖/植被指数用途，未重算核验 |
| data/ | 172文件，包括24个SHP、12个TIF、5个HTML、2个PNG及配套/历史栅格文件 | 仅为历史数据/产物资产，不当作v2效果证据 |
| outputs/ | 按run_id存放离线结果及此前pytest.xml/smoke.json | 本地生成产物，已Git忽略 |
| evals/results/ | summary.json、records.json、runs/ | 已有评测证据；本次只读取报告，未重跑评测 |

## 九、测试与评测证据

| 内容 | 覆盖/解决的问题 | 结果及口径 |
|---|---|---|
| test_request_schema.py | 单位、示例、歧义、非法距离、冲突和权重 | 本轮pytest覆盖；测试用例含参数化 |
| test_crs_and_geometry.py | 缺CRS/空/无效几何、混合CRS、非米制分析拒绝 | 本轮pytest覆盖 |
| test_gis_tools.py | 500m缓冲、交并差、栅格NoData/错位/分辨率 | 本轮pytest覆盖 |
| test_workflow.py | 确认、隔离、状态序列、真实工件、失败和empty | 本轮pytest覆盖 |
| test_site_selection.py | 硬约束、评分复算、改偏好排序和篡改拦截 | 本轮pytest覆盖；非独立GIS软件交叉核验 |
| test_security.py | 路径穿越、明显注入输入、Trace不保存输入秘密、注册器错误 | 本轮pytest覆盖；有限安全回归集 |
| test_model.py | 严格Schema、共用GIS链、清除模型确认权、拒答/坏JSON/截断/超时 | 本轮pytest覆盖；全为MockTransport |
| test_web.py | 页面、解析/确认/执行、下载、非法请求和移除危险路由 | 本轮pytest覆盖；接口测试不等于本轮浏览器目检 |
| 本轮pytest | 完整8个测试文件 | 2026-11-05实际46 passed、0 failed；1条Starlette/httpx弃用警告 |
| 本轮ruff | geosite、tests、evals静态检查 | 2026-11-05实际All checks passed |
| 本轮未确认请求 | 默认需求先解析不执行 | 实际NEEDS_CLARIFICATION，符合确认门设计 |
| 本轮确认后Demo | 默认合成选址端到端 | COMPLETED/success；144网格→77合格→Top-3；run_id=810fc4ed65cb45208813203c72340f5f |
| evals/cases.jsonl | 单/多条件、单位、歧义、无效请求、安全与数据故障 | 44条构造用例，非真实用户样本 |
| evals/run_eval.py | 断言、字段、工具、违规、空结果、耗时和环境汇总 | 程序生成JSON与Markdown；未用真实模型 |
| 现有任务验收报告 | 44条满足预期断言 | 44/44；含正确澄清和拒绝，不能称真实业务完成率100% |
| 现有字段/工具指标 | 已标注字段与按规则必要的工具调用 | 顶层字段24/24；工具20/20；不是逐槽位语义准确率或动态规划评测 |
| 现有推荐/空结果指标 | 按坐标复算硬约束、识别标注empty | 56个Top-K违规0；空结果2/2；小型合成集 |
| 弱基线 | 首数字+默认医院/within的简单解析 | 字段14/24；本轮另写的弱基线，不是原版对照 |
| API成本/token | 报告保留字段 | null/不可用；没有真实模型调用记录 |

## 十、文档逐份总结

| 文件 | 现有内容 | 解决的问题/使用价值 |
|---|---|---|
| README.md | 定位、架构、安装、演示、模型/测试入口与限制 | 降低复现门槛 |
| GeoGPT_Codex_Optimization_Prompt.md | 原始完整升级任务书 | 提供目标与验收依据；不是已完成清单 |
| docs/BASELINE.md | 原版阻断与离线替代基线 | 避免捏造原版效果 |
| docs/ARCHITECTURE_DECISIONS.md | 选项—理由—代价—验证 | 解释单工作流、固定CRS、网格与评分等取舍 |
| docs/IMPLEMENTATION_PROGRESS.md | 阶段完成/遗留和命令记录 | 避免将全部任务书标为完成 |
| docs/DELIVERY.md | 上轮52项修改/新增文件及验证摘要 | 追溯上轮交付；不自动包含后来新建文档 |
| docs/SECURITY_AUDIT.json | 凭证特征、TSD和历史审查记录 | 机器可读安全边界，不能代替凭证轮换 |
| docs/VALIDATION_RESULTS.json | 上轮测试与评测汇总 | 保留历史证据；不是本轮重新生成 |
| docs/product/PRD.md | 用户假设、流程、MVP与非目标 | 说明产品范围与验收 |
| docs/product/USER_FLOW.md | 正常、澄清、异常流程图 | 呈现用户任务路径 |
| docs/product/WIREFRAMES.md | 四区页面、字段与状态说明 | 让UI与文档对应 |
| docs/product/PRODUCT_METRICS.md | 北极星设想及各指标口径/采集 | 区分工程指标与未验证业务指标 |
| docs/evaluation/REPORT.md | 评测结果、环境、口径和未做实验 | 提供可核对实测结果 |
| docs/evaluation/BAD_CASES.md | 8类构造故障、原因、修复与回归 | 形成失败案例库 |
| docs/career/CONTRIBUTIONS.md | 上游/毕业设计/v2与AI辅助边界 | 避免夸大个人或框架贡献 |
| docs/career/PROBLEM_SOLUTION_RESULT.md | 单位、CRS、结果可信、控制边界等复盘 | 支持有证据的技术/产品追问 |
| docs/career/INTERVIEW_QA.md | 16条基于实现的问答 | 准备基础面试表达 |
| docs/career/RESUME_BULLETS.md | 已验证保守表述和待补证占位表述 | 避免编造业务收益 |
| docs/career/DEMO_SCRIPT.md | 约4分钟成功/调整/澄清演示 | 组织面试展示 |
| docs/career/INTERVIEW_GAP_AND_OPTIMIZATION.md | 招聘样本、16组追问、差距和优化验收 | 支持Agent产品实习准备；建议未自动实现 |

## 十一、安装、配置与工程化

| 内容 | 实现与用途 | 验证边界 |
|---|---|---|
| pyproject.toml | v2包元数据、Python>=3.11、依赖范围、CLI注册、打包UI、pytest/ruff配置 | 本机实测Python3.13.13；不打包旧app |
| requirements-lock.txt | 实际安装依赖版本快照 | 支持复现；不是跨平台全部环境已验证 |
| setup.py | 兼容旧构建工具的轻量入口，读取pyproject元数据 | 此前可编辑安装已验证 |
| .env.example | 列出v2和旧版所需环境变量 | 不含真实密钥，也不会自动加载.env |
| .gitignore | 忽略env、凭证、本地数据/旧静态资源、venv、缓存、运行产物 | 避免新增敏感/大型产物入库；不能删除历史凭证 |
| .github/workflows/offline.yml | Linux Python3.13安装、测试、检查、演示与评测步骤 | 只有配置，远程CI未触发验证 |
| 包初始化文件 | app/geosite/evals相关__init__和geosite/__main__ | 组织导入与python -m入口，不作为独立业务功能 |

## 十二、不能计为当前已完成的能力

| 能力 | 当前事实 | 可行的下一步 |
|---|---|---|
| 真实模型语义效果 | 只有接口和模拟测试，未实网评测 | 配置批准的模型与预算，做冻结测试集 |
| 真实城市/地块/POI选址 | 默认只用合成网格和4个图层 | 核实授权/CRS后接入真实候选点或地块 |
| 通用自主Agent/动态工具规划 | 固定单工具计划 | 出现确切任务分支需求后再扩展有界模板 |
| 原版完整兼容 | 6个TSD文件阻断，旧工具未全验收 | 取得合法明文源码后恢复基线 |
| 业务字段表单/多轮修改 | 当前JSON编辑与单次解析 | 增加定向澄清、参数diff与确认版本 |
| 实时进度/长任务取消/断点恢复 | 同步请求、新run_id重试；cancelled只在结果类型中定义 | 按真实耗时需求设计异步任务治理 |
| 空间多样性/联合覆盖/建设可行性 | 只对单点得分取Top-K | 区分替代备选与联合建设后定义目标 |
| 自动重采样/广域CRS/路网距离 | 严格栅格拒绝错位，局部米制平面距离 | 按场景引入明确策略并复核 |
| 真实用户收益和商业效果 | 没有访谈/上线/效率或费用改善证据 | 做任务观察和表单/自然语言对照 |
| 原版对照与完整消融 | 只有另写的弱解析基线 | 恢复原版并控制数据/模型/预算对照 |
| RAG/MCP/多Agent/长期记忆 | 原版有知识问答尝试；v2未集成这些系统 | 有可信语料或复用/记忆需求后再评估 |
| 生产鉴权、并发和权限管理 | 仅本地演示 | 面向多用户前补认证、配额和任务隔离 |
| 完整安全与许可核验 | 历史凭证及TSD/上游/数据授权仍有未核实项 | 轮换密钥，核实源码与数据使用授权 |
