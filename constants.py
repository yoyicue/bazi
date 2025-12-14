from __future__ import annotations

from datetime import timedelta, timezone

from lunar_python.util.LunarUtil import LunarUtil

# 五行映射
GAN_TO_ELEMENT: dict[str, str] = LunarUtil.WU_XING_GAN
ZHI_TO_ELEMENT: dict[str, str] = LunarUtil.WU_XING_ZHI
ZHI_TO_HIDDEN_GAN: dict[str, list[str]] = LunarUtil.ZHI_HIDE_GAN

# 时令对应季节
BRANCH_TO_SEASON: dict[str, str] = {
    "寅": "春",
    "卯": "春",
    "辰": "春",
    "巳": "夏",
    "午": "夏",
    "未": "夏",
    "申": "秋",
    "酉": "秋",
    "戌": "秋",
    "亥": "冬",
    "子": "冬",
    "丑": "冬",
}

# 旺相休囚死
SEASON_ELEMENT_STATUS: dict[str, dict[str, str]] = {
    "春": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
    "夏": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
    "秋": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
    "冬": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
}
STATUS_WEIGHT: dict[str, int] = {"旺": 5, "相": 4, "休": 3, "囚": 2, "死": 1}

# 五行生克
ELEMENT_MOTHER: dict[str, str] = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}
ELEMENT_CHILD: dict[str, str] = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS: dict[str, str] = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
ELEMENT_CONTROLLED_BY: dict[str, str] = {v: k for k, v in ELEMENT_CONTROLS.items()}

# 强弱：得地地势
QIANGRUO_ROOT_DISHI = {"长生", "临官", "帝旺"}

# 地支六合/冲/刑/害/破
BRANCH_LIU_HE = {frozenset(("子", "丑")), frozenset(("寅", "亥")), frozenset(("卯", "戌")), frozenset(("辰", "酉")), frozenset(("巳", "申")), frozenset(("午", "未"))}
BRANCH_LIU_CHONG = {frozenset(("子", "午")), frozenset(("丑", "未")), frozenset(("寅", "申")), frozenset(("卯", "酉")), frozenset(("辰", "戌")), frozenset(("巳", "亥"))}
BRANCH_HAI = {frozenset(("子", "未")), frozenset(("丑", "午")), frozenset(("寅", "巳")), frozenset(("卯", "辰")), frozenset(("申", "亥")), frozenset(("酉", "戌"))}
BRANCH_PO = {frozenset(("子", "酉")), frozenset(("丑", "辰")), frozenset(("寅", "亥")), frozenset(("卯", "午")), frozenset(("巳", "申")), frozenset(("未", "戌"))}
BRANCH_SELF_XING = {"辰", "午", "酉", "亥"}
BRANCH_WULI_XING = {frozenset(("子", "卯"))}
BRANCH_SANYING = {frozenset(("寅", "巳")), frozenset(("巳", "申")), frozenset(("申", "寅"))}
BRANCH_CAO_XING = {frozenset(("丑", "未")), frozenset(("未", "戌")), frozenset(("戌", "丑"))}

# 北京时区
BJ_TZ = timezone(timedelta(hours=8))
