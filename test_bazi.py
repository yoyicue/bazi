import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

from lunar_python import Solar

import bazi


class TestBaziRegression(unittest.TestCase):
    def test_true_solar_time_example(self) -> None:
        bj_tz = timezone(timedelta(hours=8))
        birth_standard = datetime(1986, 4, 6, 0, 20, 0, tzinfo=bj_tz)
        true_solar = bazi._to_true_solar_datetime(birth_standard, lon_deg=115.449444)
        self.assertEqual(true_solar, datetime(1986, 4, 5, 23, 59, 0, tzinfo=bj_tz))

    def test_yun_offset_and_start_time_example(self) -> None:
        chart_lunar = Solar.fromYmdHms(1986, 4, 6, 0, 20, 0).getLunar()
        yun_lunar = Solar.fromYmdHms(1986, 4, 5, 23, 59, 0).getLunar()

        is_forward = bazi._is_forward_yun(chart_lunar, gender=1)
        (y, m, d, h), start_solar = bazi._compute_yun(yun_lunar, is_forward=is_forward, sect=2)

        self.assertTrue(is_forward)
        self.assertEqual((y, m, d, h), (10, 0, 17, 15))
        self.assertEqual(start_solar.toYmdHms(), "1996-04-23 14:59:00")

    def test_cli_pretty_full_output_example(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bazi.main(
                [
                    "1986",
                    "4",
                    "6",
                    "0",
                    "20",
                    "--pretty",
                    "--shishen",
                    "--qiangruo",
                    "--yun",
                    "--gender",
                    "男",
                    "--true-solar",
                    "--lon",
                    "115.449444",
                    "--lat",
                    "36.490278",
                ]
            )
        self.assertEqual(rc, 0)

        out = buf.getvalue().splitlines()
        expected = [
            "真太阳时(起运用): 1986-04-05 23:59:00 (lon=115.449444, lat=36.490278)",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 庚辰",
            "时柱: 丙子",
            "年柱十神: 干=七杀 支=偏财/七杀/偏印",
            "月柱十神: 干=食神 支=偏印/正财/伤官",
            "日柱十神: 干=日主 支=偏印/正财/伤官",
            "时柱十神: 干=七杀 支=伤官",
            "日主: 庚金  强弱: 偏弱（韦千里：最弱）",
            "得令: 否 (月令=辰春，金=囚)",
            "得地: 否 (年=绝 日=养 时=死)",
            "同方(帮扶): 金1(囚) 土3(死) => 4 (加权5)",
            "异方(克泄耗): 火3(相) 木3(旺) 水4(休) => 10 (加权39)",
            "起运: 1996-04-23 14:59:00 (顺行, 出生后10年0个月17天15小时，起运虚岁 11)",
            "大运1: 癸巳 (1996-2005, 虚岁11-20)",
            "大运2: 甲午 (2006-2015, 虚岁21-30)",
            "大运3: 乙未 (2016-2025, 虚岁31-40)",
            "大运4: 丙申 (2026-2035, 虚岁41-50)",
            "大运5: 丁酉 (2036-2045, 虚岁51-60)",
            "大运6: 戊戌 (2046-2055, 虚岁61-70)",
            "大运7: 己亥 (2056-2065, 虚岁71-80)",
            "大运8: 庚子 (2066-2075, 虚岁81-90)",
            "大运9: 辛丑 (2076-2085, 虚岁91-100)",
        ]
        self.assertEqual(out, expected)

    def test_cli_pretty_shengke_output_example(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bazi.main(
                [
                    "1986",
                    "4",
                    "6",
                    "0",
                    "20",
                    "--pretty",
                    "--shishen",
                    "--shengke",
                    "--qiangruo",
                    "--yun",
                    "--gender",
                    "男",
                    "--true-solar",
                    "--lon",
                    "115.449444",
                    "--lat",
                    "36.490278",
                ]
            )
        self.assertEqual(rc, 0)

        out = buf.getvalue().splitlines()
        expected = [
            "真太阳时(起运用): 1986-04-05 23:59:00 (lon=115.449444, lat=36.490278)",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 庚辰",
            "时柱: 丙子",
            "年柱十神: 干=七杀 支=偏财/七杀/偏印",
            "月柱十神: 干=食神 支=偏印/正财/伤官",
            "日柱十神: 干=日主 支=偏印/正财/伤官",
            "时柱十神: 干=七杀 支=伤官",
            "年柱干支生克: 支寅(木) 生 干丙(火)",
            "月柱干支生克: 支辰(土) 克 干壬(水)",
            "日柱干支生克: 支辰(土) 生 干庚(金)",
            "时柱干支生克: 支子(水) 克 干丙(火)",
            "日主与天干生克: 年干丙(火) 克 日干庚(金)",
            "日主与天干生克: 日干庚(金) 生 月干壬(水)",
            "日主与天干生克: 时干丙(火) 克 日干庚(金)",
            "日主与地支生克: 日干庚(金) 克 年支寅(木)",
            "日主与地支生克: 月支辰(土) 生 日干庚(金)",
            "日主与地支生克: 日干庚(金) 生 时支子(水)",
            "年柱藏干生克泄耗帮: 甲(木)=耗 丙(火)=克 戊(土)=生",
            "月柱藏干生克泄耗帮: 戊(土)=生 乙(木)=耗 癸(水)=泄",
            "日柱藏干生克泄耗帮: 戊(土)=生 乙(木)=耗 癸(水)=泄",
            "时柱藏干生克泄耗帮: 癸(水)=泄",
            "助力(生/帮): 月支辰(土) 年柱支寅戊(土) 月柱支辰戊(土) 日柱支辰戊(土)",
            "疏泄: 月干壬(水) 时支子(水) 月柱支辰癸(水) 日柱支辰癸(水) 时柱支子癸(水)",
            "受阻(耗/克): 年干丙(火) 时干丙(火) 年支寅(木) 年柱支寅甲(木) 年柱支寅丙(火) 月柱支辰乙(木) 日柱支辰乙(木)",
            "日主: 庚金  强弱: 偏弱（韦千里：最弱）",
            "得令: 否 (月令=辰春，金=囚)",
            "得地: 否 (年=绝 日=养 时=死)",
            "同方(帮扶): 金1(囚) 土3(死) => 4 (加权5)",
            "异方(克泄耗): 火3(相) 木3(旺) 水4(休) => 10 (加权39)",
            "起运: 1996-04-23 14:59:00 (顺行, 出生后10年0个月17天15小时，起运虚岁 11)",
            "大运1: 癸巳 (1996-2005, 虚岁11-20)",
            "大运2: 甲午 (2006-2015, 虚岁21-30)",
            "大运3: 乙未 (2016-2025, 虚岁31-40)",
            "大运4: 丙申 (2026-2035, 虚岁41-50)",
            "大运5: 丁酉 (2036-2045, 虚岁51-60)",
            "大运6: 戊戌 (2046-2055, 虚岁61-70)",
            "大运7: 己亥 (2056-2065, 虚岁71-80)",
            "大运8: 庚子 (2066-2075, 虚岁81-90)",
            "大运9: 辛丑 (2076-2085, 虚岁91-100)",
        ]
        self.assertEqual(out, expected)


if __name__ == "__main__":
    unittest.main()
