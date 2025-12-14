#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from core import (
    BaziContext,
    build_context,
    compute_yun as _compute_yun,
    format_changsheng,
    format_base,
    format_hidden_gan,
    format_hechong,
    format_kongwang,
    format_lunar_info,
    format_nayin,
    format_qiangruo,
    format_shengke,
    format_shishen,
    format_shishen_flow,
    format_yongshen,
    format_wuxing_counts,
    format_yun,
    is_forward_yun as _is_forward_yun,
    parse_interactive_datetime,
    parse_gender,
    to_true_solar_datetime as _to_true_solar_datetime,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="输入年月日和小时分钟，输出命理八字（年柱 月柱 日柱 时柱），并可选输出十神、五行生克、强弱、起运和大运。"
    )
    parser.add_argument("year", type=int, nargs="?", help="年，例如 2025")
    parser.add_argument("month", type=int, nargs="?", help="月，1-12")
    parser.add_argument("day", type=int, nargs="?", help="日，1-31")
    parser.add_argument("hour", type=int, nargs="?", help="小时，0-23")
    parser.add_argument("minute", type=int, nargs="?", help="分钟，0-59")
    parser.add_argument("--second", type=int, default=0, help="秒，0-59（默认 0）")
    parser.add_argument("--pretty", action="store_true", help="输出带字段名（年柱/月柱/日柱/时柱）")
    parser.add_argument("--shishen", action="store_true", help="输出十神（天干十神与地支藏干十神）")
    parser.add_argument(
        "--shishen-flow",
        dest="shishen_flow",
        action="store_true",
        help="输出日主与各柱十神（天干+藏干）的生克泄耗帮关系",
    )
    parser.add_argument(
        "--shengke",
        "--wuxing-rel",
        dest="shengke",
        action="store_true",
        help="输出天干地支五行生克关系（柱内干支 + 日主关系 + 生克泄耗帮）",
    )
    parser.add_argument(
        "--hechong",
        "--conflict",
        dest="hechong",
        action="store_true",
        help="输出干支合/冲/刑/害/破（柱间）",
    )
    parser.add_argument(
        "--qiangruo",
        "--strength",
        dest="qiangruo",
        action="store_true",
        help="输出日主强弱判断（韦千里：得令/得地/得助、同方/异方）",
    )
    parser.add_argument("--yongshen", dest="yongshen", action="store_true", help="输出用神喜忌摘要（基于强弱）")
    parser.add_argument("--yun", "--dayun", dest="yun", action="store_true", help="输出起运和大运（需要性别）")
    parser.add_argument("--liunian", dest="liunian", action="store_true", help="输出流年（配合 --yun）")
    parser.add_argument("--liunian-count", type=int, default=10, help="流年数量（默认 10）")
    parser.add_argument("--gender", type=str, default=None, help="性别：男/女 或 1/0 或 male/female（用于起运/大运）")
    parser.add_argument(
        "--yun-sect",
        type=int,
        default=2,
        choices=(1, 2),
        help="起运流派：1=天数/时辰数，2=分钟数（默认 2）",
    )
    parser.add_argument("--true-solar", action="store_true", help="使用真太阳时（需配合 --lon；默认仅用于起运/大运计算）")
    parser.add_argument(
        "--true-solar-scope",
        type=str,
        default="yun",
        choices=("yun", "all"),
        help="真太阳时作用范围：yun=仅起运/大运，all=也用于八字/十神/强弱（默认 yun）",
    )
    parser.add_argument("--lon", type=str, default=None, help="经度（东经为正），支持 115.45 或 E115°26'58\"")
    parser.add_argument("--lat", type=str, default=None, help="纬度（北纬为正），支持 36.49 或 N36°29'25\"（当前仅用于显示）")
    parser.add_argument("--lunar-info", action="store_true", help="输出农历信息（生肖、节气、月令）")
    parser.add_argument("--hidden-gan", action="store_true", help="输出各支藏干列表")
    parser.add_argument("--wuxing-count", action="store_true", help="输出五行计数与旺衰标注")
    parser.add_argument("--changsheng", action="store_true", help="输出长生十二运")
    parser.add_argument("--nayin", action="store_true", help="输出四柱纳音")
    parser.add_argument("--kongwang", action="store_true", help="输出旬空")

    args = parser.parse_args(argv)

    provided = [args.year, args.month, args.day, args.hour, args.minute]
    if any(v is not None for v in provided) and not all(v is not None for v in provided):
        parser.error("需要同时提供 year month day hour minute，或不提供以进入交互模式。")

    if args.true_solar and not args.lon:
        parser.error("--true-solar 需要配合 --lon 提供经度。")

    if args.true_solar and args.true_solar_scope == "yun" and not args.yun:
        parser.error("--true-solar 默认仅用于起运/大运，请配合 --yun 使用，或设置 --true-solar-scope all。")

    if args.liunian and not args.yun:
        parser.error("--liunian 需要配合 --yun 使用。")

    return args


def _render_sections(ctx: BaziContext) -> list[str]:
    lines: list[str] = []

    # 基础
    lines.append("【基础】")
    lines.extend(format_base(ctx))

    # 五行
    has_wuxing = ctx.args.shengke or ctx.args.qiangruo or ctx.args.yongshen
    if has_wuxing:
        lines.append("")
        lines.append("【五行】")
        if ctx.args.shengke:
            lines.extend(format_shengke(ctx.chart_lunar, pretty=ctx.pretty))
        if ctx.args.qiangruo:
            lines.extend(format_qiangruo(ctx.chart_lunar, pretty=ctx.pretty))
        if ctx.args.yongshen:
            lines.extend(format_yongshen(ctx.chart_lunar, pretty=ctx.pretty))

    # 十神
    has_shishen = ctx.args.shishen or ctx.args.shishen_flow or ctx.args.hechong
    if has_shishen:
        lines.append("")
        lines.append("【十神】")
        if ctx.args.shishen:
            lines.extend(format_shishen(ctx.chart_lunar, pretty=ctx.pretty))
        if ctx.args.shishen_flow:
            lines.extend(format_shishen_flow(ctx.chart_lunar, pretty=ctx.pretty))
        if ctx.args.hechong:
            lines.extend(format_hechong(ctx.chart_lunar, pretty=ctx.pretty))

    # 大运
    if ctx.args.yun:
        lines.append("")
        lines.append("【大运】")
        if ctx.gender is not None:
            lines.extend(
                format_yun(
                    ctx.chart_lunar,
                    ctx.yun_lunar,
                    gender=ctx.gender,
                    sect=ctx.args.yun_sect,
                    pretty=ctx.pretty,
                    prefix="",
                    show_liunian=ctx.args.liunian,
                    liunian_count=ctx.args.liunian_count,
                )
            )
        else:
            # 性别未知时，同时输出男/女两套
            lines.extend(
                format_yun(
                    ctx.chart_lunar,
                    ctx.yun_lunar,
                    gender=1,
                    sect=ctx.args.yun_sect,
                    pretty=ctx.pretty,
                    prefix="男 ",
                    show_liunian=ctx.args.liunian,
                    liunian_count=ctx.args.liunian_count,
                )
            )
            lines.extend(
                format_yun(
                    ctx.chart_lunar,
                    ctx.yun_lunar,
                    gender=0,
                    sect=ctx.args.yun_sect,
                    pretty=ctx.pretty,
                    prefix="女 ",
                    show_liunian=ctx.args.liunian,
                    liunian_count=ctx.args.liunian_count,
                )
            )

    # 扩展事实（客观信息，不做喜忌判断）
    has_extra = (
        ctx.args.lunar_info
        or ctx.args.hidden_gan
        or ctx.args.wuxing_count
        or ctx.args.changsheng
        or ctx.args.nayin
        or ctx.args.kongwang
    )
    if has_extra:
        lines.append("")
        lines.append("【扩展事实】")
        if ctx.args.lunar_info:
            lines.extend(format_lunar_info(ctx.chart_lunar))
        if ctx.args.hidden_gan:
            lines.extend(format_hidden_gan(ctx.chart_lunar))
        if ctx.args.wuxing_count:
            lines.extend(format_wuxing_counts(ctx.chart_lunar))
        if ctx.args.changsheng:
            lines.extend(format_changsheng(ctx.chart_lunar))
        if ctx.args.nayin:
            lines.extend(format_nayin(ctx.chart_lunar))
        if ctx.args.kongwang:
            lines.extend(format_kongwang(ctx.chart_lunar))

    return lines


def main(argv: list[str] | None = None) -> int:
    args = parse_args([] if argv is None else argv)
    ctx = build_context(args)
    lines = _render_sections(ctx)
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


# 兼容测试/外部使用的导出
__all__ = ["main", "_to_true_solar_datetime", "_is_forward_yun", "_compute_yun", "parse_gender", "parse_interactive_datetime"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
