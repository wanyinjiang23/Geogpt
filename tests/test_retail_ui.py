from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]/"ui"/"retail_app.py"


def button(at, label):
    return next(x for x in at.button if x.label == label)


def checkbox(at, label):
    return next(x for x in at.checkbox if x.label == label)


def test_five_pages_and_full_interaction():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    button(at, "解析需求").click().run()
    assert at.session_state.flow.request.months == 6
    button(at, "进入经营诊断 →").click().run()
    assert button(at, "确认口径并分析").disabled
    checkbox(at, "我已确认指标定义、时间窗口和可比门店范围").check().run()
    button(at, "确认口径并分析").click().run()
    assert at.session_state.flow.analysis is not None
    next(x for x in at.multiselect if x.label == "展示店型").set_value([]).run()
    assert not at.exception
    button(at, "基于当前分析制定拓店策略 →").click().run()
    at.slider[0].set_value(0).run()
    assert button(at, "确认策略并开始筛选").disabled
    at.slider[0].set_value(50).run()
    checkbox(at, "我确认以上硬约束、评分规则和数据局限").check().run()
    button(at, "确认策略并开始筛选").click().run()
    assert at.session_state.flow.state == "COMPLETED"
    button(at, "查看已执行的候选结果 →").click().run()
    assert not at.exception
    choice = next(x for x in at.selectbox if x.label == "选择候选区域")
    choice.set_value(choice.options[-1]).run()
    assert not at.exception
    button(at, "查看分析记录与报告").click().run()
    assert not at.exception
    assert len(at.session_state.flow.trace) >= 6


def test_empty_pages_and_parse_error():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    for page in ["门店经营诊断", "拓店策略", "候选商圈", "分析记录与报告", "经营分析总览"]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception
    at.text_area[0].set_value("分析利润率").run()
    button(at, "解析需求").click().run()
    assert at.session_state.flow.state == "NEEDS_CLARIFICATION"
    assert at.error
