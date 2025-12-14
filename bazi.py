#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from lunar_python import Lunar
from lunar_python import Solar
from lunar_python.eightchar.DaYun import DaYun
from lunar_python.util.LunarUtil import LunarUtil

GAN_TO_ELEMENT: dict[str, str] = LunarUtil.WU_XING_GAN
ZHI_TO_ELEMENT: dict[str, str] = LunarUtil.WU_XING_ZHI
ZHI_TO_HIDDEN_GAN: dict[str, list[str]] = LunarUtil.ZHI_HIDE_GAN

BJ_TZ = timezone(timedelta(hours=8))

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

SEASON_ELEMENT_STATUS: dict[str, dict[str, str]] = {
    "春": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
    "夏": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
    "秋": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
    "冬": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
}

STATUS_WEIGHT: dict[str, int] = {"旺": 5, "相": 4, "休": 3, "囚": 2, "死": 1}

ELEMENT_MOTHER: dict[str, str] = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}
ELEMENT_CHILD: dict[str, str] = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS: dict[str, str] = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
ELEMENT_CONTROLLED_BY: dict[str, str] = {
    "木": "金",
    "火": "水",
    "土": "木",
    "金": "火",
    "水": "土",
}

QIANGRUO_ROOT_DISHI = {"长生", "临官", "帝旺"}


@dataclass(frozen=True)
class BaziContext:
    args: argparse.Namespace
    pretty: bool
    gender: int | None

    birth_standard_dt: datetime
    lon_deg: float | None
    lat_deg: float | None
    true_solar_dt: datetime | None

    chart_lunar: Lunar
    yun_lunar: Lunar


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="输入年月日和小时分钟，输出命理八字（年柱 月柱 日柱 时柱），并可选输出十神、起运和大运。"
    )
    parser.add_argument("year", type=int, nargs="?", help="年，例如 2025")
    parser.add_argument("month", type=int, nargs="?", help="月，1-12")
    parser.add_argument("day", type=int, nargs="?", help="日，1-31")
    parser.add_argument("hour", type=int, nargs="?", help="小时，0-23")
    parser.add_argument("minute", type=int, nargs="?", help="分钟，0-59")
    parser.add_argument("--second", type=int, default=0, help="秒，0-59（默认 0）")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="输出带字段名（年柱/月柱/日柱/时柱）",
    )
    parser.add_argument(
        "--shishen",
        action="store_true",
        help="输出十神（天干十神与地支藏干十神）",
    )
    parser.add_argument(
        "--shengke",
        "--wuxing-rel",
        dest="shengke",
        action="store_true",
        help="输出天干地支五行生克关系（柱内干支 + 日主关系 + 生克泄耗帮）",
    )
    parser.add_argument(
        "--shishen-flow",
        dest="shishen_flow",
        action="store_true",
        help="输出日主与各柱十神（天干+藏干）的生克泄耗帮关系",
    )
    parser.add_argument(
        "--qiangruo",
        "--strength",
        dest="qiangruo",
        action="store_true",
        help="输出日主强弱判断（韦千里：得令/得地/得助、同方/异方）",
    )
    parser.add_argument(
        "--yun",
        "--dayun",
        dest="yun",
        action="store_true",
        help="输出起运和大运（需要性别；未提供则同时输出男/女）",
    )
    parser.add_argument(
        "--gender",
        type=str,
        default=None,
        help="性别：男/女 或 1/0 或 male/female（用于起运/大运）",
    )
    parser.add_argument(
        "--yun-sect",
        type=int,
        default=2,
        choices=(1, 2),
        help="起运流派：1=天数/时辰数，2=分钟数（默认 2）",
    )
    parser.add_argument(
        "--true-solar",
        action="store_true",
        help="使用真太阳时（需配合 --lon；默认仅用于起运/大运计算）",
    )
    parser.add_argument(
        "--true-solar-scope",
        type=str,
        default="yun",
        choices=("yun", "all"),
        help="真太阳时作用范围：yun=仅起运/大运，all=也用于八字/十神/强弱（默认 yun）",
    )
    parser.add_argument(
        "--lon",
        type=str,
        default=None,
        help="经度（东经为正），支持 115.45 或 E115°26'58\"",
    )
    parser.add_argument(
        "--lat",
        type=str,
        default=None,
        help="纬度（北纬为正），支持 36.49 或 N36°29'25\"（当前仅用于显示）",
    )
    args = parser.parse_args(argv)

    provided = [args.year, args.month, args.day, args.hour, args.minute]
    if any(v is not None for v in provided) and not all(v is not None for v in provided):
        parser.error("需要同时提供 year month day hour minute，或不提供以进入交互模式。")

    if args.true_solar and not args.lon:
        parser.error("--true-solar 需要配合 --lon 提供经度。")

    if args.true_solar and args.true_solar_scope == "yun" and not args.yun:
        parser.error("--true-solar 默认仅用于起运/大运，请配合 --yun 使用，或设置 --true-solar-scope all。")

    return args


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


def _format_shishen_zhi(values: list[str]) -> str:
    return "/".join(values) if values else "-"


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


def _split_ganzhi(ganzhi: str) -> tuple[str, str]:
    if len(ganzhi) < 2:
        raise ValueError(f"无效干支：{ganzhi!r}")
    return ganzhi[0], ganzhi[1]


def _calc_wuxing_counts(gans: list[str], zhis: list[str]) -> dict[str, int]:
    counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for gan in gans:
        counts[GAN_TO_ELEMENT[gan]] += 1
    for zhi in zhis:
        for hidden_gan in ZHI_TO_HIDDEN_GAN[zhi]:
            counts[GAN_TO_ELEMENT[hidden_gan]] += 1
    return counts


def _format_wuxing_breakdown(
    counts: dict[str, int], status_map: dict[str, str], elements: list[str]
) -> str:
    return " ".join(f"{e}{counts[e]}({status_map[e]})" for e in elements)


def _weiqianli_qiangruo_level(*, de_ling: bool, de_di: bool, multi_support: bool, multi_hostile: bool) -> str:
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


def _assess_qiangruo(lunar) -> dict[str, object]:
    bazi = lunar.getBaZi()
    gans = []
    zhis = []
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
    diff_elements = [
        ELEMENT_CONTROLLED_BY[day_element],  # 克我
        ELEMENT_CONTROLS[day_element],  # 我克
        ELEMENT_CHILD[day_element],  # 我生
    ]

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

    eight_char = lunar.getEightChar()
    di_shi = {
        "年": eight_char.getYearDiShi(),
        "日": eight_char.getDayDiShi(),
        "时": eight_char.getTimeDiShi(),
    }
    de_di = any(v in QIANGRUO_ROOT_DISHI for v in di_shi.values())

    level = _weiqianli_qiangruo_level(
        de_ling=de_ling, de_di=de_di, multi_support=multi_support, multi_hostile=multi_hostile
    )

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
    }


def _print_qiangruo(lunar, *, pretty: bool) -> None:
    info = _assess_qiangruo(lunar)
    counts = info["counts"]
    status_map = SEASON_ELEMENT_STATUS.get(info["season"], {e: "?" for e in ("木", "火", "土", "金", "水")})
    same_line = _format_wuxing_breakdown(counts, status_map, info["same_elements"])
    diff_line = _format_wuxing_breakdown(counts, status_map, info["diff_elements"])

    if pretty:
        print(f"日主: {info['day_gan']}{info['day_element']}  强弱: {info['bias']}（韦千里：{info['level']}）")
        print(
            f"得令: {'是' if info['de_ling'] else '否'} (月令={info['month_zhi']}{info['season']}，{info['day_element']}={info['day_element_status']})"
        )
        di_shi = info["di_shi"]
        print(
            f"得地: {'是' if info['de_di'] else '否'} (年={di_shi['年']} 日={di_shi['日']} 时={di_shi['时']})"
        )
        print(
            f"同方(帮扶): {same_line} => {info['same_count']} (加权{info['same_power']})"
        )
        print(
            f"异方(克泄耗): {diff_line} => {info['diff_count']} (加权{info['diff_power']})"
        )
    else:
        print(
            f"{info['day_gan']}{info['day_element']} {info['bias']}({info['level']}) 得令={'Y' if info['de_ling'] else 'N'} 得地={'Y' if info['de_di'] else 'N'} 同方={info['same_count']} 异方={info['diff_count']}"
        )


def _parse_gender(value: str) -> int:
    value = value.strip().lower()
    if value in {"1", "m", "male", "man", "boy", "男"}:
        return 1
    if value in {"0", "f", "female", "woman", "girl", "女"}:
        return 0
    raise ValueError("性别需要为：男/女 或 1/0 或 male/female")


def _parse_degrees(value: str, *, kind: str) -> float:
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


def _to_true_solar_datetime(local_standard_dt: datetime, *, lon_deg: float) -> datetime:
    # 中国常用北京时间（UTC+8）标准经线为东经120度。
    tz_meridian = 120.0
    correction_minutes = 4.0 * (lon_deg - tz_meridian) + _equation_of_time_minutes(
        local_standard_dt
    )
    return _round_datetime_to_minute(local_standard_dt + timedelta(minutes=correction_minutes))


def _solar_from_datetime(dt: datetime) -> Solar:
    try:
        return Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    except Exception as exc:
        raise ValueError(f"输入时间无效：{exc}") from exc


def _lunar_from_datetime(dt: datetime) -> Lunar:
    return _solar_from_datetime(dt).getLunar()


def _build_context(args: argparse.Namespace) -> BaziContext:
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
        try:
            gender = _parse_gender(args.gender)
        except ValueError as exc:
            raise ValueError(f"性别参数无效：{exc}") from exc

    birth_standard_dt = datetime(year, month, day, hour, minute, second, tzinfo=BJ_TZ)

    lon_deg: float | None = None
    lat_deg: float | None = None
    true_solar_dt: datetime | None = None
    if args.true_solar:
        try:
            lon_deg = _parse_degrees(args.lon or "", kind="lon")
            if args.lat:
                lat_deg = _parse_degrees(args.lat, kind="lat")
        except ValueError as exc:
            raise ValueError(f"经纬度参数无效：{exc}") from exc
        true_solar_dt = _to_true_solar_datetime(birth_standard_dt, lon_deg=lon_deg)

    chart_dt = (
        true_solar_dt
        if args.true_solar and args.true_solar_scope == "all" and true_solar_dt is not None
        else birth_standard_dt
    )
    chart_lunar = _lunar_from_datetime(chart_dt)

    yun_lunar = chart_lunar
    if args.yun and args.true_solar and args.true_solar_scope == "yun" and true_solar_dt is not None:
        yun_lunar = _lunar_from_datetime(true_solar_dt)

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


def _print_true_solar_header(ctx: BaziContext) -> None:
    if not ctx.pretty or not ctx.args.true_solar or ctx.true_solar_dt is None or ctx.lon_deg is None:
        return
    label = "真太阳时" if ctx.args.true_solar_scope == "all" else "真太阳时(起运用)"
    lat_text = f", lat={ctx.lat_deg:.6f}" if ctx.lat_deg is not None else ""
    print(
        f"{label}: {ctx.true_solar_dt.strftime('%Y-%m-%d %H:%M:%S')} (lon={ctx.lon_deg:.6f}{lat_text})"
    )


def _print_bazi(lunar: Lunar, *, pretty: bool) -> None:
    pillars = lunar.getBaZi()
    if pretty:
        labels = ["年柱", "月柱", "日柱", "时柱"]
        for label, pillar in zip(labels, pillars):
            print(f"{label}: {pillar}")
    else:
        print(" ".join(pillars))


def _print_shishen(lunar: Lunar, *, pretty: bool) -> None:
    eight_char = lunar.getEightChar()
    gan = [
        eight_char.getYearShiShenGan(),
        eight_char.getMonthShiShenGan(),
        eight_char.getDayShiShenGan(),
        eight_char.getTimeShiShenGan(),
    ]
    zhi = [
        _format_shishen_zhi(eight_char.getYearShiShenZhi()),
        _format_shishen_zhi(eight_char.getMonthShiShenZhi()),
        _format_shishen_zhi(eight_char.getDayShiShenZhi()),
        _format_shishen_zhi(eight_char.getTimeShiShenZhi()),
    ]

    if pretty:
        labels = ["年柱", "月柱", "日柱", "时柱"]
        for i, label in enumerate(labels):
            print(f"{label}十神: 干={gan[i]} 支={zhi[i]}")
    else:
        print(" ".join(gan))
        print(" ".join(zhi))


def _print_shishen_flow(lunar: Lunar, *, pretty: bool) -> None:
    pillars = lunar.getBaZi()
    gans: list[str] = []
    zhis: list[str] = []
    for pillar in pillars:
        gan, zhi = _split_ganzhi(pillar)
        gans.append(gan)
        zhis.append(zhi)

    day_gan = gans[2]
    day_element = GAN_TO_ELEMENT[day_gan]

    def _cat(other_element: str) -> str:
        return _relation_category(day_element, other_element)

    labels = ["年柱", "月柱", "日柱", "时柱"]
    for i, label in enumerate(labels):
        gan = gans[i]
        gan_element = GAN_TO_ELEMENT[gan]
        gan_line = f"干{gan}({gan_element})={_cat(gan_element)}"
        hides = ZHI_TO_HIDDEN_GAN[zhis[i]]
        hides_line = " ".join(f"{hide}({GAN_TO_ELEMENT[hide]})={_cat(GAN_TO_ELEMENT[hide])}" for hide in hides)
        if pretty:
            print(f"{label}十神流通(干): {gan_line}")
            if hides:
                print(f"{label}十神流通(藏干): {hides_line}")
        else:
            print(f"{label}(干):{gan_line}")
            if hides:
                print(f"{label}(藏):{hides_line}")


def _print_section(title: str, *, first: bool, pretty: bool) -> None:
    if not pretty:
        return
    if not first:
        print()
    print(f"【{title}】")


def _describe_wuxing_relation(
    a_label: str,
    a_char: str,
    a_element: str,
    b_label: str,
    b_char: str,
    b_element: str,
) -> str:
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


def _print_shengke(lunar: Lunar, *, pretty: bool) -> None:
    pillars = lunar.getBaZi()
    gans: list[str] = []
    zhis: list[str] = []
    for pillar in pillars:
        gan, zhi = _split_ganzhi(pillar)
        gans.append(gan)
        zhis.append(zhi)

    pillar_labels = ["年柱", "月柱", "日柱", "时柱"]
    for i, pillar_label in enumerate(pillar_labels):
        gan = gans[i]
        zhi = zhis[i]
        gan_element = GAN_TO_ELEMENT[gan]
        zhi_element = ZHI_TO_ELEMENT[zhi]
        desc = _describe_wuxing_relation("干", gan, gan_element, "支", zhi, zhi_element)
        if pretty:
            print(f"{pillar_label}干支生克: {desc}")
        else:
            print(f"{pillar_label}:{desc}")

    day_gan = gans[2]
    day_element = GAN_TO_ELEMENT[day_gan]
    relations: list[tuple[str, str]] = []

    for idx, label in ((0, "年干"), (1, "月干"), (3, "时干")):
        other_gan = gans[idx]
        other_element = GAN_TO_ELEMENT[other_gan]
        desc = _describe_wuxing_relation("日干", day_gan, day_element, label, other_gan, other_element)
        relations.append((f"{label}{other_gan}({other_element})", _relation_category(day_element, other_element)))
        if pretty:
            print(f"日主与天干生克: {desc}")
        else:
            print(desc)

    for idx, label in ((0, "年支"), (1, "月支"), (3, "时支")):
        other_zhi = zhis[idx]
        other_element = ZHI_TO_ELEMENT[other_zhi]
        desc = _describe_wuxing_relation("日干", day_gan, day_element, label, other_zhi, other_element)
        relations.append((f"{label}{other_zhi}({other_element})", _relation_category(day_element, other_element)))
        if pretty:
            print(f"日主与地支生克: {desc}")
        else:
            print(desc)

    # 藏干生克泄耗帮
    for i, pillar_label in enumerate(pillar_labels):
        zhi = zhis[i]
        hidden = ZHI_TO_HIDDEN_GAN[zhi]
        if not hidden:
            continue
        parts = []
        for gan in hidden:
            element = GAN_TO_ELEMENT[gan]
            cat = _relation_category(day_element, element)
            relations.append((f"{pillar_label}支{zhi}{gan}({element})", cat))
            parts.append(f"{gan}({element})={cat}")
        line = " ".join(parts)
        if pretty:
            print(f"{pillar_label}藏干生克泄耗帮: {line}")
        else:
            print(f"{pillar_label}藏干:{line}")

    # 汇总
    assist = [label for label, cat in relations if cat in {"生", "帮"}]
    leak = [label for label, cat in relations if cat == "泄"]
    hinder = [label for label, cat in relations if cat in {"耗", "克"}]
    if pretty:
        print(f"助力(生/帮): {' '.join(assist) if assist else '-'}")
        print(f"疏泄: {' '.join(leak) if leak else '-'}")
        print(f"受阻(耗/克): {' '.join(hinder) if hinder else '-'}")
    else:
        print(f"助力:{' '.join(assist)}")
        print(f"泄:{' '.join(leak)}")
        print(f"耗克:{' '.join(hinder)}")


def _solar_to_datetime(solar: Solar) -> datetime:
    return datetime(
        solar.getYear(),
        solar.getMonth(),
        solar.getDay(),
        solar.getHour(),
        solar.getMinute(),
        solar.getSecond(),
    )


def _is_forward_yun(lunar, *, gender: int) -> bool:
    yang_year = lunar.getYearGanIndexExact() % 2 == 0
    return (yang_year and gender == 1) or ((not yang_year) and gender == 0)


def _compute_yun(lunar, *, is_forward: bool, sect: int) -> tuple[tuple[int, int, int, int], Solar]:
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
        end_time_zhi_index = (
            11
            if end_boundary.getHour() == 23
            else LunarUtil.getTimeZhiIndex(end_boundary.toYmdHms()[11:16])
        )
        start_time_zhi_index = (
            11
            if start_boundary.getHour() == 23
            else LunarUtil.getTimeZhiIndex(start_boundary.toYmdHms()[11:16])
        )
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


def _format_yun_offset(year: int, month: int, day: int, hour: int) -> str:
    return f"{year}年{month}个月{day}天{hour}小时"


class _YunDuck:
    def __init__(self, lunar, *, start_solar: Solar, forward: bool):
        self.__lunar = lunar
        self.__start_solar = start_solar
        self.__forward = forward

    def getLunar(self):
        return self.__lunar

    def getStartSolar(self):
        return self.__start_solar

    def isForward(self):
        return self.__forward


def _print_yun(chart_lunar, yun_lunar, *, gender: int, sect: int, pretty: bool, prefix: str) -> None:
    is_forward = _is_forward_yun(chart_lunar, gender=gender)
    (y, m, d, h), start_solar = _compute_yun(yun_lunar, is_forward=is_forward, sect=sect)
    direction = "顺行" if is_forward else "逆行"
    start_offset = _format_yun_offset(y, m, d, h)

    birth_year = chart_lunar.getSolar().getYear()
    first_dayun_age = start_solar.getYear() - birth_year + 1
    start_age_text = f"，起运虚岁 {first_dayun_age}"

    yun_duck = _YunDuck(chart_lunar, start_solar=start_solar, forward=is_forward)
    dayun_list = [DaYun(yun_duck, i) for i in range(1, 10)]

    if pretty:
        print(f"{prefix}起运: {start_solar.toYmdHms()} ({direction}, 出生后{start_offset}{start_age_text})")
        for item in dayun_list:
            print(
                f"{prefix}大运{item.getIndex()}: {item.getGanZhi()} ({item.getStartYear()}-{item.getEndYear()}, 虚岁{item.getStartAge()}-{item.getEndAge()})"
            )
    else:
        print(f"{prefix}{start_solar.toYmdHms()} {direction} {start_offset}")
        parts = [f"{item.getStartYear()}{item.getGanZhi()}" for item in dayun_list]
        print(f"{prefix}" + " ".join(parts))


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        ctx = _build_context(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    section_first = True
    _print_section("基础", first=section_first, pretty=ctx.pretty)
    section_first = False
    _print_true_solar_header(ctx)
    _print_bazi(ctx.chart_lunar, pretty=ctx.pretty)

    if args.shengke or args.qiangruo:
        _print_section("五行", first=section_first, pretty=ctx.pretty)
        section_first = False
        if args.shengke:
            _print_shengke(ctx.chart_lunar, pretty=ctx.pretty)
        if args.qiangruo:
            _print_qiangruo(ctx.chart_lunar, pretty=ctx.pretty)

    if args.shishen:
        _print_section("十神", first=section_first, pretty=ctx.pretty)
        section_first = False
        _print_shishen(ctx.chart_lunar, pretty=ctx.pretty)
        if args.shishen_flow:
            _print_shishen_flow(ctx.chart_lunar, pretty=ctx.pretty)

    if args.yun:
        _print_section("大运", first=section_first, pretty=ctx.pretty)
        if ctx.gender is None:
            if ctx.pretty:
                _print_yun(
                    ctx.chart_lunar,
                    ctx.yun_lunar,
                    gender=1,
                    sect=args.yun_sect,
                    pretty=ctx.pretty,
                    prefix="男",
                )
                _print_yun(
                    ctx.chart_lunar,
                    ctx.yun_lunar,
                    gender=0,
                    sect=args.yun_sect,
                    pretty=ctx.pretty,
                    prefix="女",
                )
            else:
                _print_yun(
                    ctx.chart_lunar,
                    ctx.yun_lunar,
                    gender=1,
                    sect=args.yun_sect,
                    pretty=ctx.pretty,
                    prefix="男 ",
                )
                _print_yun(
                    ctx.chart_lunar,
                    ctx.yun_lunar,
                    gender=0,
                    sect=args.yun_sect,
                    pretty=ctx.pretty,
                    prefix="女 ",
                )
        else:
            _print_yun(
                ctx.chart_lunar,
                ctx.yun_lunar,
                gender=ctx.gender,
                sect=args.yun_sect,
                pretty=ctx.pretty,
                prefix="",
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
