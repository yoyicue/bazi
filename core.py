from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from lunar_python import Lunar, Solar
from lunar_python.eightchar.DaYun import DaYun
from lunar_python.util.LunarUtil import LunarUtil

from constants import (
    BJ_TZ,
    BRANCH_CAO_XING,
    BRANCH_HAI,
    BRANCH_LIU_CHONG,
    BRANCH_LIU_HE,
    BRANCH_PO,
    BRANCH_SANYING,
    BRANCH_SELF_XING,
    BRANCH_TO_SEASON,
    BRANCH_WULI_XING,
    ELEMENT_CHILD,
    ELEMENT_CONTROLLED_BY,
    ELEMENT_CONTROLS,
    ELEMENT_MOTHER,
    GAN_TO_ELEMENT,
    QIANGRUO_ROOT_DISHI,
    SEASON_ELEMENT_STATUS,
    STATUS_WEIGHT,
    ZHI_TO_ELEMENT,
    ZHI_TO_HIDDEN_GAN,
)


@dataclass(frozen=True)
class BaziContext:
    args: object  # argparse.Namespace-like
    pretty: bool
    gender: int | None
    birth_standard_dt: datetime
    lon_deg: float | None
    lat_deg: float | None
    true_solar_dt: datetime | None
    chart_lunar: Lunar
    yun_lunar: Lunar


def parse_interactive_datetime() -> tuple[int, int, int, int, int, int] | None:
    try:
        date_str = input("请输入公历日期 (YYYY-MM-DD)：").strip()
        time_str = input("请输入时间 (HH:MM 或 HH:MM:SS)：").strip()
    except EOFError:
        return None

    if not date_str or not time_str:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", fmt)
            return dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
        except ValueError:
            pass
    return None


def parse_gender(value: str) -> int:
    value = value.strip().lower()
    if value in {"1", "m", "male", "man", "boy", "男"}:
        return 1
    if value in {"0", "f", "female", "woman", "girl", "女"}:
        return 0
    raise ValueError("性别需要为：男/女 或 1/0 或 male/female")


def parse_degrees(value: str, *, kind: str) -> float:
    s = value.strip().upper()
    if not s:
        raise ValueError("为空")
    sign = 1.0
    if any(h in s for h in ("W", "S")):
        sign = -1.0
    if any(h in s for h in ("E", "N")):
        sign = 1.0
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", s)
    if not nums:
        raise ValueError("无法解析")
    if len(nums) == 1:
        deg = float(nums[0])
        if deg < 0:
            sign = -1.0
            deg = abs(deg)
    else:
        d = float(nums[0])
        m = float(nums[1]) if len(nums) >= 2 else 0.0
        sec = float(nums[2]) if len(nums) >= 3 else 0.0
        if d < 0:
            sign = -1.0
            d = abs(d)
        deg = d + m / 60.0 + sec / 3600.0
    deg *= sign
    if kind == "lon" and not (-180.0 <= deg <= 180.0):
        raise ValueError("经度范围应为 -180~180")
    if kind == "lat" and not (-90.0 <= deg <= 90.0):
        raise ValueError("纬度范围应为 -90~90")
    return deg


def _equation_of_time_minutes(local_standard_dt: datetime) -> float:
    n = local_standard_dt.timetuple().tm_yday
    fractional_hour = (
        local_standard_dt.hour
        + local_standard_dt.minute / 60.0
        + local_standard_dt.second / 3600.0
    )
    gamma = 2.0 * math.pi / 365.0 * (n - 1 + (fractional_hour - 12.0) / 24.0)
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )


def _round_datetime_to_minute(dt: datetime) -> datetime:
    if dt.second >= 30:
        dt = dt + timedelta(minutes=1)
    return dt.replace(second=0, microsecond=0)


def to_true_solar_datetime(local_standard_dt: datetime, *, lon_deg: float) -> datetime:
    tz_meridian = 120.0  # 北京时间标准经线
    correction_minutes = 4.0 * (lon_deg - tz_meridian) + _equation_of_time_minutes(local_standard_dt)
    return _round_datetime_to_minute(local_standard_dt + timedelta(minutes=correction_minutes))


def solar_from_datetime(dt: datetime) -> Solar:
    return Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def lunar_from_datetime(dt: datetime) -> Lunar:
    return solar_from_datetime(dt).getLunar()


def _split_ganzhi(gz: str) -> tuple[str, str]:
    if len(gz) < 2:
        raise ValueError(f"无效干支：{gz!r}")
    return gz[0], gz[1]


def build_context(args) -> BaziContext:
    if args.year is None:
        parsed = parse_interactive_datetime()
        if parsed is None:
            raise ValueError("输入格式不正确。示例：2025-12-14 和 12:00")
        year, month, day, hour, minute, second = parsed
        pretty = True
    else:
        year, month, day, hour, minute, second = (
            args.year,
            args.month,
            args.day,
            args.hour,
            args.minute,
            args.second,
        )
        pretty = args.pretty

    gender: int | None = None
    if args.gender is not None:
        gender = parse_gender(args.gender)

    birth_standard_dt = datetime(year, month, day, hour, minute, second, tzinfo=BJ_TZ)

    lon_deg: float | None = None
    lat_deg: float | None = None
    true_solar_dt: datetime | None = None
    if args.true_solar:
        lon_deg = parse_degrees(args.lon or "", kind="lon")
        if args.lat:
            lat_deg = parse_degrees(args.lat, kind="lat")
        true_solar_dt = to_true_solar_datetime(birth_standard_dt, lon_deg=lon_deg)

    chart_dt = (
        true_solar_dt
        if args.true_solar and args.true_solar_scope == "all" and true_solar_dt is not None
        else birth_standard_dt
    )
    chart_lunar = lunar_from_datetime(chart_dt)

    yun_lunar = chart_lunar
    if args.yun and args.true_solar and args.true_solar_scope == "yun" and true_solar_dt is not None:
        yun_lunar = lunar_from_datetime(true_solar_dt)

    return BaziContext(
        args=args,
        pretty=pretty,
        gender=gender,
        birth_standard_dt=birth_standard_dt,
        lon_deg=lon_deg,
        lat_deg=lat_deg,
        true_solar_dt=true_solar_dt,
        chart_lunar=chart_lunar,
        yun_lunar=yun_lunar,
    )


def format_base(ctx: BaziContext) -> list[str]:
    lines: list[str] = []
    if ctx.pretty and ctx.args.true_solar and ctx.true_solar_dt is not None and ctx.lon_deg is not None:
        label = "真太阳时" if ctx.args.true_solar_scope == "all" else "真太阳时(起运用)"
        lat_text = f", lat={ctx.lat_deg:.6f}" if ctx.lat_deg is not None else ""
        lines.append(f"{label}: {ctx.true_solar_dt.strftime('%Y-%m-%d %H:%M:%S')} (lon={ctx.lon_deg:.6f}{lat_text})")
    pillars = ctx.chart_lunar.getBaZi()
    if ctx.pretty:
        labels = ["年柱", "月柱", "日柱", "时柱"]
        for label, pillar in zip(labels, pillars):
            lines.append(f"{label}: {pillar}")
    else:
        lines.append(" ".join(pillars))
    return lines


def _calc_wuxing_counts(gans: list[str], zhis: list[str]) -> dict[str, int]:
    counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for gan in gans:
        counts[GAN_TO_ELEMENT[gan]] += 1
    for zhi in zhis:
        for hide in ZHI_TO_HIDDEN_GAN[zhi]:
            counts[GAN_TO_ELEMENT[hide]] += 1
    return counts


def _weiqianli_level(*, de_ling: bool, de_di: bool, multi_support: bool, multi_hostile: bool) -> str:
    if de_ling:
        if multi_support:
            return "最强"
        if multi_hostile:
            return "中弱"
        if not de_di:
            return "次弱"
        return "中和"
    if multi_support:
        return "中强"
    if multi_hostile:
        return "最弱"
    if de_di:
        return "次强"
    return "偏弱"


def assess_qiangruo(lunar: Lunar) -> dict[str, object]:
    bazi = lunar.getBaZi()
    gans: list[str] = []
    zhis: list[str] = []
    for pillar in bazi:
        gan, zhi = _split_ganzhi(pillar)
        gans.append(gan)
        zhis.append(zhi)

    day_gan = gans[2]
    day_element = GAN_TO_ELEMENT[day_gan]
    month_zhi = zhis[1]
    season = BRANCH_TO_SEASON.get(month_zhi, "?")
    status_map = SEASON_ELEMENT_STATUS.get(season, {e: "?" for e in ("木", "火", "土", "金", "水")})
    day_element_status = status_map[day_element]
    de_ling = day_element_status in {"旺", "相"}

    counts = _calc_wuxing_counts(gans, zhis)

    same_elements = [day_element, ELEMENT_MOTHER[day_element]]
    diff_elements = [ELEMENT_CONTROLLED_BY[day_element], ELEMENT_CONTROLS[day_element], ELEMENT_CHILD[day_element]]

    same_count = sum(counts[e] for e in same_elements)
    diff_count = sum(counts[e] for e in diff_elements)
    same_power = sum(counts[e] * STATUS_WEIGHT[status_map[e]] for e in same_elements)
    diff_power = sum(counts[e] * STATUS_WEIGHT[status_map[e]] for e in diff_elements)

    multi_support = same_power >= diff_power * 1.2 if diff_power > 0 else True
    multi_hostile = diff_power >= same_power * 1.2 if same_power > 0 else True

    if same_power >= diff_power * 1.1:
        bias = "偏强"
    elif diff_power >= same_power * 1.1:
        bias = "偏弱"
    else:
        bias = "平和"

    ec = lunar.getEightChar()
    di_shi = {"年": ec.getYearDiShi(), "日": ec.getDayDiShi(), "时": ec.getTimeDiShi()}
    de_di = any(v in QIANGRUO_ROOT_DISHI for v in di_shi.values())

    level = _weiqianli_level(de_ling=de_ling, de_di=de_di, multi_support=multi_support, multi_hostile=multi_hostile)

    return {
        "day_gan": day_gan,
        "day_element": day_element,
        "month_zhi": month_zhi,
        "season": season,
        "day_element_status": day_element_status,
        "de_ling": de_ling,
        "di_shi": di_shi,
        "de_di": de_di,
        "counts": counts,
        "same_elements": same_elements,
        "diff_elements": diff_elements,
        "same_count": same_count,
        "diff_count": diff_count,
        "same_power": same_power,
        "diff_power": diff_power,
        "bias": bias,
        "level": level,
        "status_map": status_map,
    }


def format_qiangruo(lunar: Lunar, *, pretty: bool) -> list[str]:
    info = assess_qiangruo(lunar)
    lines: list[str] = []
    status_map = info["status_map"]
    counts = info["counts"]
    same_line = " ".join(f"{e}{counts[e]}({status_map[e]})" for e in info["same_elements"])
    diff_line = " ".join(f"{e}{counts[e]}({status_map[e]})" for e in info["diff_elements"])
    if pretty:
        lines.append(f"日主: {info['day_gan']}{info['day_element']}  强弱: {info['bias']}（韦千里：{info['level']}）")
        lines.append(
            f"得令: {'是' if info['de_ling'] else '否'} (月令={info['month_zhi']}{info['season']}，{info['day_element']}={info['day_element_status']})"
        )
        di_shi = info["di_shi"]
        lines.append(f"得地: {'是' if info['de_di'] else '否'} (年={di_shi['年']} 日={di_shi['日']} 时={di_shi['时']})")
        lines.append(f"同方(帮扶): {same_line} => {info['same_count']} (加权{info['same_power']})")
        lines.append(f"异方(克泄耗): {diff_line} => {info['diff_count']} (加权{info['diff_power']})")
    else:
        lines.append(
            f"{info['day_gan']}{info['day_element']} {info['bias']}({info['level']}) 得令={'Y' if info['de_ling'] else 'N'} 得地={'Y' if info['de_di'] else 'N'} 同方={info['same_count']} 异方={info['diff_count']}"
        )
    return lines


def format_yongshen(lunar: Lunar, *, pretty: bool) -> list[str]:
    info = assess_qiangruo(lunar)
    day_element = info["day_element"]
    bias = info["bias"]
    status_map = info["status_map"]
    if bias == "偏弱":
        main_useful = [day_element, ELEMENT_MOTHER[day_element]]
        warn = [ELEMENT_CONTROLS[day_element], ELEMENT_CONTROLLED_BY[day_element]]
        desc = "身弱扶抑：取比劫印为喜，用以扶身；财官为忌，勿再耗克。"
    elif bias == "偏强":
        main_useful = [ELEMENT_CHILD[day_element], ELEMENT_CONTROLS[day_element]]
        warn = [day_element, ELEMENT_MOTHER[day_element]]
        desc = "身强泄耗：取食伤财为喜，泄耗日主；比劫印为忌，避免再扶。"
    else:
        main_useful = [day_element]
        warn = []
        desc = "平和：喜忌不偏，宜结合大运流年与格局再定。"

    def fmt(items: list[str]) -> str:
        return " ".join(f"{e}({status_map.get(e, '?')})" for e in items) if items else "-"

    lines: list[str] = []
    if pretty:
        lines.append(f"用神喜忌: {desc}")
        lines.append(f"喜用五行: {fmt(main_useful)}")
        lines.append(f"忌五行: {fmt(warn)}")
    else:
        lines.append(f"喜用:{fmt(main_useful)} 忌:{fmt(warn)} {desc}")
    return lines


def format_lunar_info(lunar: Lunar) -> list[str]:
    lines: list[str] = []
    lines.append(f"阴历: {lunar.getYearInChinese()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}日")
    lines.append(f"生肖: {lunar.getYearShengXiao()}")
    prev_jie = lunar.getPrevJie()
    next_jie = lunar.getNextJie()
    lines.append(
        f"节气: 上一{prev_jie.getName()} {prev_jie.getSolar().toYmdHms()}  下一{next_jie.getName()} {next_jie.getSolar().toYmdHms()}"
    )
    lines.append(f"月令: {lunar.getMonthInGanZhi()} ({lunar.getMonthShengXiao()}月)")
    return lines


def format_hidden_gan(lunar: Lunar) -> list[str]:
    pillars = lunar.getBaZi()
    zhis = [p[1] for p in pillars]
    labels = ["年支", "月支", "日支", "时支"]
    lines: list[str] = []
    for label, zhi in zip(labels, zhis):
        hides = ZHI_TO_HIDDEN_GAN[zhi]
        hides_str = " ".join(hides) if hides else "-"
        lines.append(f"{label}{zhi} 藏干: {hides_str}")
    return lines


def format_wuxing_counts(lunar: Lunar) -> list[str]:
    pillars = lunar.getBaZi()
    gans = [p[0] for p in pillars]
    zhis = [p[1] for p in pillars]
    month_zhi = zhis[1]
    season = BRANCH_TO_SEASON.get(month_zhi, "?")
    status_map = SEASON_ELEMENT_STATUS.get(season, {e: "?" for e in ("木", "火", "土", "金", "水")})
    counts = _calc_wuxing_counts(gans, zhis)
    parts = [f"{e}{counts[e]}({status_map.get(e, '?')})" for e in ("木", "火", "土", "金", "水")]
    return [f"五行计数: {' '.join(parts)}"]


def format_changsheng(lunar: Lunar) -> list[str]:
    ec = lunar.getEightChar()
    lines: list[str] = []
    lines.append(
        f"长生十二运: 年={ec.getYearDiShi()} 月={ec.getMonthDiShi()} 日={ec.getDayDiShi()} 时={ec.getTimeDiShi()}"
    )
    return lines


def format_nayin(lunar: Lunar) -> list[str]:
    ec = lunar.getEightChar()
    lines: list[str] = []
    lines.append(
        f"纳音: 年={ec.getYearNaYin()} 月={ec.getMonthNaYin()} 日={ec.getDayNaYin()} 时={ec.getTimeNaYin()}"
    )
    return lines


def format_kongwang(lunar: Lunar) -> list[str]:
    pillars = lunar.getBaZi()
    labels = ["年柱", "月柱", "日柱", "时柱"]
    lines: list[str] = []
    for label, gz in zip(labels, pillars):
        lines.append(f"{label}旬空: {LunarUtil.getXunKong(gz)}")
    return lines


def _relation_category(day_element: str, other_element: str) -> str:
    if day_element == other_element:
        return "帮"
    if ELEMENT_MOTHER[day_element] == other_element:
        return "生"
    if ELEMENT_CHILD[day_element] == other_element:
        return "泄"
    if ELEMENT_CONTROLS[day_element] == other_element:
        return "耗"
    if ELEMENT_CONTROLLED_BY[day_element] == other_element:
        return "克"
    return "?"


def _describe_wuxing_relation(a_label: str, a_char: str, a_element: str, b_label: str, b_char: str, b_element: str) -> str:
    if a_element == b_element:
        return f"{a_label}{a_char}({a_element}) 同 {b_label}{b_char}({b_element})"
    if ELEMENT_CHILD[a_element] == b_element:
        return f"{a_label}{a_char}({a_element}) 生 {b_label}{b_char}({b_element})"
    if ELEMENT_CHILD[b_element] == a_element:
        return f"{b_label}{b_char}({b_element}) 生 {a_label}{a_char}({a_element})"
    if ELEMENT_CONTROLS[a_element] == b_element:
        return f"{a_label}{a_char}({a_element}) 克 {b_label}{b_char}({b_element})"
    if ELEMENT_CONTROLS[b_element] == a_element:
        return f"{b_label}{b_char}({b_element}) 克 {a_label}{a_char}({a_element})"
    return f"{a_label}{a_char}({a_element}) ? {b_label}{b_char}({b_element})"


def format_shengke(lunar: Lunar, *, pretty: bool) -> list[str]:
    pillars = lunar.getBaZi()
    gans: list[str] = []
    zhis: list[str] = []
    for pillar in pillars:
        gan, zhi = _split_ganzhi(pillar)
        gans.append(gan)
        zhis.append(zhi)
    lines: list[str] = []
    labels = ["年柱", "月柱", "日柱", "时柱"]
    for i, label in enumerate(labels):
        gan, zhi = gans[i], zhis[i]
        gan_element = GAN_TO_ELEMENT[gan]
        zhi_element = ZHI_TO_ELEMENT[zhi]
        desc = _describe_wuxing_relation("支", zhi, zhi_element, "干", gan, gan_element)
        if pretty:
            lines.append(f"{label}干支生克: {desc}")
        else:
            lines.append(f"{label}:{desc}")
    day_gan = gans[2]
    day_element = GAN_TO_ELEMENT[day_gan]
    relations: list[tuple[str, str]] = []
    for idx, lab in ((0, "年干"), (1, "月干"), (3, "时干")):
        other = gans[idx]
        oe = GAN_TO_ELEMENT[other]
        desc = _describe_wuxing_relation("日干", day_gan, day_element, lab, other, oe)
        relations.append((f"{lab}{other}({oe})", _relation_category(day_element, oe)))
        lines.append(f"日主与天干生克: {desc}" if pretty else desc)
    for idx, lab in ((0, "年支"), (1, "月支"), (3, "时支")):
        other = zhis[idx]
        oe = ZHI_TO_ELEMENT[other]
        desc = _describe_wuxing_relation("日干", day_gan, day_element, lab, other, oe)
        relations.append((f"{lab}{other}({oe})", _relation_category(day_element, oe)))
        lines.append(f"日主与地支生克: {desc}" if pretty else desc)
    # 藏干
    for i, pillar_label in enumerate(labels):
        zhi = zhis[i]
        hidden = ZHI_TO_HIDDEN_GAN[zhi]
        if not hidden:
            continue
        parts = []
        for hide in hidden:
            he = GAN_TO_ELEMENT[hide]
            cat = _relation_category(day_element, he)
            relations.append((f"{pillar_label}支{zhi}{hide}({he})", cat))
            parts.append(f"{hide}({he})={cat}")
        line = " ".join(parts)
        lines.append(f"{pillar_label}藏干生克泄耗帮: {line}" if pretty else f"{pillar_label}藏干:{line}")
    assist = [label for label, cat in relations if cat in {"生", "帮"}]
    leak = [label for label, cat in relations if cat == "泄"]
    hinder = [label for label, cat in relations if cat in {"耗", "克"}]
    if pretty:
        lines.append(f"助力(生/帮): {' '.join(assist) if assist else '-'}")
        lines.append(f"疏泄: {' '.join(leak) if leak else '-'}")
        lines.append(f"受阻(耗/克): {' '.join(hinder) if hinder else '-'}")
    else:
        lines.append(f"助力:{' '.join(assist)}")
        lines.append(f"泄:{' '.join(leak)}")
        lines.append(f"耗克:{' '.join(hinder)}")
    return lines


def format_shishen(lunar: Lunar, *, pretty: bool) -> list[str]:
    ec = lunar.getEightChar()
    gan = [ec.getYearShiShenGan(), ec.getMonthShiShenGan(), ec.getDayShiShenGan(), ec.getTimeShiShenGan()]
    zhi = [
        "/".join(ec.getYearShiShenZhi()) or "-",
        "/".join(ec.getMonthShiShenZhi()) or "-",
        "/".join(ec.getDayShiShenZhi()) or "-",
        "/".join(ec.getTimeShiShenZhi()) or "-",
    ]
    labels = ["年柱", "月柱", "日柱", "时柱"]
    lines: list[str] = []
    if pretty:
        for i, label in enumerate(labels):
            lines.append(f"{label}十神: 干={gan[i]} 支={zhi[i]}")
    else:
        lines.append(" ".join(gan))
        lines.append(" ".join(zhi))
    return lines


def format_shishen_flow(lunar: Lunar, *, pretty: bool) -> list[str]:
    pillars = lunar.getBaZi()
    gans = [p[0] for p in pillars]
    zhis = [p[1] for p in pillars]
    day_element = GAN_TO_ELEMENT[gans[2]]
    labels = ["年柱", "月柱", "日柱", "时柱"]
    lines: list[str] = []
    for i, label in enumerate(labels):
        gan = gans[i]
        zhi = zhis[i]
        gan_line = f"干{gan}({GAN_TO_ELEMENT[gan]})={_relation_category(day_element, GAN_TO_ELEMENT[gan])}"
        zhi_line = f"支{zhi}({ZHI_TO_ELEMENT[zhi]})={_relation_category(day_element, ZHI_TO_ELEMENT[zhi])}"
        hides = ZHI_TO_HIDDEN_GAN[zhi]
        hides_line = " ".join(f"{h}({GAN_TO_ELEMENT[h]})={_relation_category(day_element, GAN_TO_ELEMENT[h])}" for h in hides)
        if pretty:
            lines.append(f"{label}十神流通(干): {gan_line}")
            lines.append(f"{label}十神流通(支): {zhi_line}")
            if hides:
                lines.append(f"{label}十神流通(藏干): {hides_line}")
        else:
            lines.append(f"{label}(干):{gan_line}")
            lines.append(f"{label}(支):{zhi_line}")
            if hides:
                lines.append(f"{label}(藏):{hides_line}")
    return lines


def _branch_relations(a: str, b: str) -> list[str]:
    rels: list[str] = []
    if a == b and a in BRANCH_SELF_XING:
        rels.append("自刑")
    if frozenset((a, b)) in BRANCH_LIU_HE:
        rels.append("六合")
    if frozenset((a, b)) in BRANCH_LIU_CHONG:
        rels.append("冲")
    if frozenset((a, b)) in BRANCH_SANYING or frozenset((a, b)) in BRANCH_CAO_XING or frozenset((a, b)) in BRANCH_WULI_XING:
        rels.append("刑")
    if frozenset((a, b)) in BRANCH_HAI:
        rels.append("害")
    if frozenset((a, b)) in BRANCH_PO:
        rels.append("破")
    return rels


def format_hechong(lunar: Lunar, *, pretty: bool) -> list[str]:
    pillars = lunar.getBaZi()
    labels = ["年柱", "月柱", "日柱", "时柱"]
    gans = [p[0] for p in pillars]
    zhis = [p[1] for p in pillars]
    stem_he_map = {
        frozenset(("甲", "己")): "合",
        frozenset(("乙", "庚")): "合",
        frozenset(("丙", "辛")): "合",
        frozenset(("丁", "壬")): "合",
        frozenset(("戊", "癸")): "合",
    }
    stem_lines: list[str] = []
    branch_lines: list[str] = []
    for i in range(len(pillars)):
        for j in range(i + 1, len(pillars)):
            tag = f"{labels[i]}-{labels[j]}"
            gan_rel = stem_he_map.get(frozenset((gans[i], gans[j])))
            if gan_rel:
                stem_lines.append(f"{tag}: 干{gans[i]}∪{gans[j]} {gan_rel}")
            zrel = _branch_relations(zhis[i], zhis[j])
            if zrel:
                branch_lines.append(f"{tag}: 支{zhis[i]}∪{zhis[j]} {'/'.join(zrel)}")
    lines: list[str] = []
    if pretty:
        if stem_lines:
            lines.append("天干合: " + "; ".join(stem_lines))
        if branch_lines:
            lines.append("地支合冲刑害破: " + "; ".join(branch_lines))
        if not stem_lines and not branch_lines:
            lines.append("合冲刑害破: 无显著关系")
    else:
        if stem_lines:
            lines.append("干合:" + ";".join(stem_lines))
        if branch_lines:
            lines.append("支合冲刑害破:" + ";".join(branch_lines))
        if not stem_lines and not branch_lines:
            lines.append("合冲刑害破:无")
    return lines


def is_forward_yun(lunar: Lunar, *, gender: int) -> bool:
    yang_year = lunar.getYearGanIndexExact() % 2 == 0
    return (yang_year and gender == 1) or ((not yang_year) and gender == 0)


def _solar_to_datetime(sol: Solar) -> datetime:
    return datetime(sol.getYear(), sol.getMonth(), sol.getDay(), sol.getHour(), sol.getMinute(), sol.getSecond())


def compute_yun(lunar: Lunar, *, is_forward: bool, sect: int) -> tuple[tuple[int, int, int, int], Solar]:
    prev_jie = lunar.getPrevJie()
    next_jie = lunar.getNextJie()
    current = lunar.getSolar()
    start_boundary = current if is_forward else prev_jie.getSolar()
    end_boundary = next_jie.getSolar() if is_forward else current
    if sect == 2:
        start_dt = _solar_to_datetime(start_boundary)
        end_dt = _solar_to_datetime(end_boundary)
        total_minutes = (end_dt - start_dt).total_seconds() / 60.0
        year = int(total_minutes // 4320)
        total_minutes -= year * 4320
        month = int(total_minutes // 360)
        total_minutes -= month * 360
        day = int(total_minutes // 12)
        total_minutes -= day * 12
        hour = int(total_minutes * 2)
    else:
        end_time_zhi_index = 11 if end_boundary.getHour() == 23 else LunarUtil.getTimeZhiIndex(end_boundary.toYmdHms()[11:16])
        start_time_zhi_index = 11 if start_boundary.getHour() == 23 else LunarUtil.getTimeZhiIndex(start_boundary.toYmdHms()[11:16])
        hour_diff = end_time_zhi_index - start_time_zhi_index
        day_diff = end_boundary.subtract(start_boundary)
        if hour_diff < 0:
            hour_diff += 12
            day_diff -= 1
        month_diff = int(hour_diff * 10 / 30)
        month = day_diff * 4 + month_diff
        day = hour_diff * 10 - month_diff * 30
        year = int(month / 12)
        month = month - year * 12
        hour = 0
    start_solar = current.nextYear(year).nextMonth(month).next(day).nextHour(hour)
    return (year, month, day, hour), start_solar


def format_yun(
    chart_lunar: Lunar,
    yun_lunar: Lunar,
    *,
    gender: int,
    sect: int,
    pretty: bool,
    prefix: str,
    show_liunian: bool,
    liunian_count: int,
) -> list[str]:
    lines: list[str] = []
    forward = is_forward_yun(chart_lunar, gender=gender)
    (y, m, d, h), start_solar = compute_yun(yun_lunar, is_forward=forward, sect=sect)
    direction = "顺行" if forward else "逆行"
    start_offset = f"{y}年{m}个月{d}天{h}小时"
    birth_year = chart_lunar.getSolar().getYear()
    first_dayun_age = start_solar.getYear() - birth_year + 1
    if pretty:
        lines.append(f"{prefix}起运: {start_solar.toYmdHms()} ({direction}, 出生后{start_offset}，起运虚岁 {first_dayun_age})")
    else:
        lines.append(f"{prefix}{start_solar.toYmdHms()} {direction} {start_offset}")

    class _YunDuck:
        def __init__(self, lunar, start_solar, forward: bool):
            self.__lunar = lunar
            self.__start_solar = start_solar
            self.__forward = forward

        def getLunar(self):
            return self.__lunar

        def getStartSolar(self):
            return self.__start_solar

        def isForward(self):
            return self.__forward

    yun_duck = _YunDuck(chart_lunar, start_solar=start_solar, forward=forward)
    dayun_list = [DaYun(yun_duck, i) for i in range(1, 10)]
    for item in dayun_list:
        if pretty:
            lines.append(
                f"{prefix}大运{item.getIndex()}: {item.getGanZhi()} ({item.getStartYear()}-{item.getEndYear()}, 虚岁{item.getStartAge()}-{item.getEndAge()})"
            )
            if show_liunian:
                liu_nian = item.getLiuNian(liunian_count)
                liu_str = " ".join(f"{ln.getYear()}{ln.getGanZhi()}(虚岁{ln.getAge()})" for ln in liu_nian)
                lines.append(f"{prefix}  流年: {liu_str}")
        else:
            lines.append(f"{prefix}{item.getStartYear()}{item.getGanZhi()}")
    return lines
