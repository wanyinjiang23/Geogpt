"""Five-page Streamlit prototype sharing one controlled workflow."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from georetail.data import generate, SOURCE
from georetail.parser import DEMO_PROMPT
from georetail.schema import Strategy
from georetail.workflow import RetailWorkflow

st.set_page_config(page_title="GeoRetail · CoffeeLab", page_icon="☕", layout="wide")
st.markdown("""<style>
.stApp {background:#f5f7fb;color:#162c3a}
[data-testid="stSidebar"] {background:#102f36;color:#e4f3ef}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {color:#e4f3ef}
[data-testid="stSidebar"] [data-testid="stAlert"] [data-testid="stMarkdownContainer"] {color:#16475b}
[data-testid="stSidebar"] [role="combobox"] {color:#162c3a}
[data-testid="stMetric"] {background:white;border:1px solid #e3e9ef;border-radius:12px;padding:18px}
h1 {letter-spacing:-1px} h3 {color:#23584e}
.stButton>button[kind="primary"] {background:#126b59;border-color:#126b59}
.stMainBlockContainer {padding-top:2.5rem}
@media (max-width:1100px) {
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] {flex-wrap:wrap}
  [data-testid="stMain"] [data-testid="stColumn"] {min-width:280px}
}
</style>""", unsafe_allow_html=True)
PAGES = ["经营分析总览", "门店经营诊断", "拓店策略", "候选商圈", "分析记录与报告"]
METRICS = {"经营利润率": "margin", "营业额": "revenue", "经营利润": "profit", "订单量": "orders", "同店前期增长率": "growth"}
if "flow" not in st.session_state:
    st.session_state.flow = RetailWorkflow(generate())
if "history" not in st.session_state:
    st.session_state.history = []
flow = st.session_state.flow
b = flow.bundle


def go(page):
    st.session_state.page = page


def remember():
    root = Path(__file__).resolve().parents[2] / "过程文件" / "GeoRetail_20261109" / "runs"
    flow.save(root)
    item = {"任务": flow.run_id, "状态": flow.state, "报告": flow.report()}
    st.session_state.history = [x for x in st.session_state.history if x["任务"] != flow.run_id]+[item]


with st.sidebar:
    st.markdown("## ◈ GeoRetail\nCoffeeLab 决策工作空间")
    st.caption("RETAIL INTELLIGENCE / MVP 1.0")
    st.radio("工作空间", PAGES, key="page")
    st.divider()
    st.selectbox("执行模式", ["offline", "llm"], key="mode", format_func=lambda x: "离线 · 规则演示" if x == "offline" else "在线 · 模型参数解析")
    st.caption("在线模式仅发送问题文本，不发送经营表或GIS文件；需自行配置环境变量。")
    st.info("全部经营及空间数据为模拟数据。用于流程验证，不代表真实上海商圈。")
    status_slot = st.empty()

page = st.session_state.page
st.caption("COFFEELAB  /  区域经营与拓店辅助决策")
st.title(page)
st.caption(SOURCE+" · 数据期：2025-01—2025-12 · 最近月份相对演示数据末月")
if flow.error:
    st.error(flow.error)

if page == PAGES[0]:
    st.markdown("从经营表现出发，发现值得进一步验证的拓店机会。")
    a, c, d = st.columns(3)
    a.selectbox("品牌", ["CoffeeLab"])
    c.selectbox("城市", ["上海（模拟区域）"])
    months = d.slider("经营时间范围（月）", 1, 12, 6, key="overview_months")
    monthly = b.monthly[b.monthly.month >= f"2025-{13-months:02}"]
    cols = st.columns(4)
    for col, label, value in zip(cols, ["营业额", "订单量", "经营利润", "活跃门店"],
        [f"¥{monthly.revenue.sum():,.0f}", f"{monthly.orders.sum():,}", f"¥{monthly.profit.sum():,.0f}", str(monthly.store_id.nunique())]):
        col.metric(label, value)
    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("经营趋势")
        st.line_chart(monthly.groupby("month")[["revenue", "profit"]].sum(), color=["#126b59", "#c99948"])
    with right:
        st.subheader("门店经营分布")
        values = monthly.groupby("store_id").revenue.sum()
        st.bar_chart(pd.cut(values, bins=5).value_counts(sort=False).rename_axis("营业额区间").reset_index(name="门店数").assign(营业额区间=lambda x: x.营业额区间.astype(str)).set_index("营业额区间"), color="#126b59")
    st.subheader("向 Agent 发起分析")
    st.caption("离线规则支持最近1—12个月、利润率/营业额/利润/订单/增长率、成熟门店、前N家；其他条件会要求澄清。")
    prompt = st.text_area("业务问题", DEMO_PROMPT, height=90, key="prompt")
    st.caption("上方时间控件用于总览；提交问题后可在诊断页核对并修改实际分析窗口。")
    if st.button("解析需求", type="primary"):
        with st.spinner("解析问题并校验参数…"):
            flow.prepare(prompt, st.session_state.mode)
        if flow.request:
            st.success("参数已解析，请前往诊断页确认指标口径。")
        else:
            st.error(flow.error)
    if flow.request:
        st.json(flow.request.model_dump(), expanded=False)
        st.button("进入经营诊断 →", on_click=go, args=(PAGES[1],))
    st.subheader("最近分析任务")
    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history).drop(columns="报告"), hide_index=True)
    else:
        st.info("暂无已执行任务。解析问题并确认指标后开始。")

elif page == PAGES[1]:
    if flow.request is None:
        st.info("请先在总览输入问题并解析需求。")
        st.button("返回总览", on_click=go, args=(PAGES[0],))
    else:
        st.subheader("01 / 确认分析口径")
        st.info("经营利润＝收入－材料－人工－租金－其他成本（模拟经营口径，非审计净利润）；利润率＝窗口总利润/窗口总收入。成熟店＝窗口起点店龄≥12个月；只比较完整窗口门店。")
        c1, c2, c3 = st.columns(3)
        metric_labels = list(METRICS)
        label = c1.selectbox("排名指标", metric_labels, index=list(METRICS.values()).index(flow.request.metric))
        months = c2.number_input("最近月数", 1, 12, flow.request.months)
        count = c3.number_input("优秀门店样本数", 1, 50, flow.request.top_n)
        mature = st.checkbox("仅成熟门店", value=flow.request.mature_only)
        confirm = st.checkbox("我已确认指标定义、时间窗口和可比门店范围", key="confirm_metrics")
        if st.button("确认口径并分析", type="primary", disabled=not confirm):
            with st.spinner("调用经营分析工具…"):
                request = flow.request.model_dump() | {"metric": METRICS[label], "months": months, "top_n": count, "mature_only": mature}
                flow.diagnose(confirmed=True, request=request)
                remember()
        if flow.analysis:
            result = flow.analysis
            st.success(result["summary"])
            st.caption(f"已执行口径：{result['period']}；排序指标 {flow.request.metric}。修改上方控件后需重新确认执行。排除不完整窗口门店 {result['excluded_count']} 家。")
            types = st.multiselect("展示店型", list(b.stores.store_type.unique()), default=list(b.stores.store_type.unique()))
            rows = result["ranking"][result["ranking"].store_type.isin(types)]
            st.subheader("门店排名与对比")
            st.dataframe(rows[["store_id", "name", "store_type", "area_type", "revenue", "profit", "margin", "growth"]], hide_index=True)
            if not rows.empty:
                store = st.selectbox("查看门店详情", rows.store_id.tolist())
                st.dataframe(rows[rows.store_id == store].T.astype(str))
                st.bar_chart(rows.head(10).set_index("store_id")[[flow.request.metric]], color="#126b59")
            st.subheader("分组比较与相关特征")
            a, c = st.columns(2)
            a.dataframe(result["groups"], hide_index=True)
            c.dataframe(result["comparison"], hide_index=True)
            with st.expander("查看 Pearson 相关系数及样本局限"):
                st.dataframe(result["correlation"])
                st.caption("优秀样本与其余样本均来自模拟数据；分组未控制混杂因素。其余样本为空或方差为零时相关结果不可用。")
            st.button("基于当前分析制定拓店策略 →", type="primary", on_click=go, args=(PAGES[2],))

elif page == PAGES[2]:
    if not flow.analysis:
        st.info("请先完成经营诊断，策略需要关联已确认的分析。")
    else:
        st.subheader("02 / 从观察到待验证的规则")
        st.info(flow.analysis["summary"])
        st.warning("建议验证需求设施、交通便利性和竞争环境。以下默认距离和权重为演示假设，未从历史相关性自动转成硬约束。用户修改并确认后才执行。")
        defaults = flow.strategy or Strategy()
        a, c = st.columns(2)
        with a:
            st.selectbox("目标城市", ["上海（模拟区域）"])
            region = st.selectbox("目标区域", ["全部", "北区", "南区"], index=["全部", "北区", "南区"].index(defaults.region))
            st.subheader("硬性约束")
            minimum = st.number_input("距现有店至少（米）", 0., 20000., float(defaults.min_store_m), step=100.)
            maximum = st.number_input("距交通点不超过（米）", 1., 20000., float(defaults.max_transit_m), step=100.)
            competitors = st.number_input("服务区内竞品最多（家）", 0, 100, defaults.max_competitors)
            radius = st.number_input("服务区半径（米）", 100., 5000., float(defaults.radius_m), step=100.)
        with c:
            st.subheader("软性评价权重")
            dw = st.slider("需求设施权重", 0, 100, int(defaults.demand_weight))
            tw = st.slider("交通便利权重", 0, 100, int(defaults.transit_weight))
            cw = st.slider("竞争环境权重", 0, 100, int(defaults.competition_weight))
            total = dw+tw+cw
            st.metric("权重合计", f"{total}%")
            if total != 100:
                st.error("权重合计必须为100%，请修改后确认。")
            st.caption("需求分=min(需求POI数/10,1)×100；交通分=max(0,1−距离/3000)×100；竞争分=max(0,1−竞品数/20)×100。综合分为三项加权和。固定锚点为人工假设。")
            st.caption("可用：模拟门店、POI与候选点。不可用：真实客流、租金、产权、路网；缺失项不参与评分。")
        confirmed = st.checkbox("我确认以上硬约束、评分规则和数据局限", key="confirm_strategy")
        if st.button("确认策略并开始筛选", type="primary", disabled=not confirmed or total != 100):
            try:
                with st.spinner("执行缓冲区、距离与叠置分析…"):
                    flow.screen(Strategy(region=region, min_store_m=minimum, max_transit_m=maximum,
                        max_competitors=competitors, radius_m=radius, demand_weight=dw,
                        transit_weight=tw, competition_weight=cw).model_dump(), confirmed=True)
                    remember()
                st.success("筛选已完成，请查看候选商圈。")
            except ValueError as exc:
                st.error(str(exc))
        if flow.strategy_confirmed:
            st.button("查看已执行的候选结果 →", on_click=go, args=(PAGES[3],))

elif page == PAGES[3]:
    if flow.state == "EMPTY":
        st.warning("没有符合全部硬约束的候选点；以下计数可重叠，不表示连续空间无可行商圈。")
        st.json(flow.rejected)
    elif flow.candidates.empty:
        st.info("暂无候选结果，请完成策略确认和筛选。")
    else:
        rows = flow.candidates
        st.success(f"返回 {len(rows)} 个符合约束的模拟候选商圈 · 评分不是新店收入或利润预测")
        selected_key = f"selected_{len(flow.trace)}"
        if "map_site" in st.session_state and st.session_state.map_site in rows.site_id.tolist():
            st.session_state[selected_key] = st.session_state.pop("map_site")
        selected_id = st.selectbox("选择候选区域", rows.site_id.tolist(), key=selected_key)
        site = rows[rows.site_id == selected_id].iloc[0]
        left, right = st.columns([1.7, 1])
        with left:
            st.subheader("空间视图")
            show_tiles = st.checkbox("加载公开地图底图（需要网络）", value=False)
            m = folium.Map(location=[site.lat, site.lon], zoom_start=12, tiles="OpenStreetMap" if show_tiles else None)
            for _, s in b.stores.iterrows():
                folium.CircleMarker([s.lat, s.lon], radius=3, color="#aab7bf", tooltip=s.store_id).add_to(m)
            for _, s in rows.iterrows():
                folium.CircleMarker([s.lat, s.lon], radius=10 if s.site_id == selected_id else 7,
                    color="#126b59", fill=True, fill_opacity=.8, tooltip=s.site_id, popup=s["name"]).add_to(m)
                folium.Circle([s.lat, s.lon], radius=flow.strategy.radius_m, color="#126b59", weight=1, fill_opacity=.05).add_to(m)
            event = st_folium(m, height=430, use_container_width=True, key="candidate_map", returned_objects=["last_object_clicked"])
            clicked = (event or {}).get("last_object_clicked")
            if clicked:
                nearest = rows.assign(delta=(rows.lat-clicked["lat"])**2+(rows.lon-clicked["lng"])**2).sort_values("delta").iloc[0]
                signature = (clicked["lat"], clicked["lng"])
                if nearest.delta < 1e-8 and st.session_state.get("last_click") != signature:
                    st.session_state.last_click = signature
                    st.session_state.map_site = nearest.site_id
                    st.rerun()
            st.caption("灰色点为现有店；圆形为模拟服务区。Folium组件首次加载需要网络资源；无网络时使用下方本地坐标视图。")
            with st.expander("本地坐标视图（不依赖地图服务）"):
                st.scatter_chart(rows, x="x", y="y", color="#126b59", size="score")
        with right:
            st.subheader(str(site["name"]))
            st.metric("综合评分", f"{site.score:.1f} / 100")
            st.write(f"现有店间距 {site.nearest_store_m:.0f} m · 交通点 {site.transit_m:.0f} m")
            st.write(f"竞品 {site.competitors} 家 · 需求设施 {site.demand} 处")
            st.write(f"潜在服务区重叠 {site.overlap_ratio:.1%}")
            st.success("全部硬约束已通过确定性校验")
            st.bar_chart(pd.Series({"需求": site.demand_score, "交通": site.transit_score, "竞争": site.competition_score}), color="#126b59")
            st.write("优势：可复核的设施、交通、竞争指标符合当前规则。")
            st.warning("风险：设施不等于客流，圆形覆盖不等于步行可达。请实地核查租金、权属与竞品营业情况。")
        st.dataframe(rows[["site_id", "name", "score", "nearest_store_m", "transit_m", "competitors", "demand", "overlap_ratio"]], hide_index=True)
        st.download_button("导出候选CSV", rows.to_csv(index=False).encode("utf-8-sig"), "CoffeeLab_candidates.csv")
    st.button("调整策略", on_click=go, args=(PAGES[2],))
    st.button("查看分析记录与报告", on_click=go, args=(PAGES[4],))

elif page == PAGES[4]:
    st.metric("任务状态", flow.state)
    if flow.trace:
        st.subheader("受控 Agent 执行轨迹")
        st.dataframe(pd.DataFrame(flow.trace).astype(str), hide_index=True)
        st.caption("耗时由本机 perf_counter 实测；离线模式无模型调用，模型成本为0。在线费用需结合服务商账单，本系统未计价。")
    else:
        st.info("暂无执行轨迹。")
    st.markdown(flow.report())
    st.download_button("下载 Markdown 报告", flow.report(), "CoffeeLab_report.md")
    if st.session_state.history:
        task = st.selectbox("查看本次会话历史任务", [x["任务"] for x in st.session_state.history])
        entry = next(x for x in st.session_state.history if x["任务"] == task)
        with st.expander("历史报告"):
            st.markdown(entry["报告"])
    st.caption("执行产物自动保存在 D:/Geogpt/过程文件/GeoRetail_20261109/runs。会话历史列表重启后清空，已保存文件保留。")

status_slot.caption(f"当前任务状态：{flow.state}")
