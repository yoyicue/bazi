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
            "【基础】",
            "真太阳时(起运用): 1986-04-05 23:59:00 (lon=115.449444, lat=36.490278)",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 庚辰",
            "时柱: 丙子",
            "",
            "【五行】",
            "日主: 庚金  强弱: 偏弱（韦千里：最弱）",
            "得令: 否 (月令=辰春，金=囚)",
            "得地: 否 (年=绝 日=养 时=死)",
            "同方(帮扶): 金1(囚) 土3(死) => 4 (加权5)",
            "异方(克泄耗): 火3(相) 木3(旺) 水4(休) => 10 (加权39)",
            "",
            "【十神】",
            "年柱十神: 干=七杀 支=偏财/七杀/偏印",
            "月柱十神: 干=食神 支=偏印/正财/伤官",
            "日柱十神: 干=日主 支=偏印/正财/伤官",
            "时柱十神: 干=七杀 支=伤官",
            "",
            "【大运】",
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
                    "--shishen-flow",
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
            "【基础】",
            "真太阳时(起运用): 1986-04-05 23:59:00 (lon=115.449444, lat=36.490278)",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 庚辰",
            "时柱: 丙子",
            "",
            "【五行】",
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
            "",
            "【十神】",
            "年柱十神: 干=七杀 支=偏财/七杀/偏印",
            "月柱十神: 干=食神 支=偏印/正财/伤官",
            "日柱十神: 干=日主 支=偏印/正财/伤官",
            "时柱十神: 干=七杀 支=伤官",
            "年柱十神流通(干): 干丙(火)=克",
            "年柱十神流通(支): 支寅(木)=耗",
            "年柱十神流通(藏干): 甲(木)=耗 丙(火)=克 戊(土)=生",
            "月柱十神流通(干): 干壬(水)=泄",
            "月柱十神流通(支): 支辰(土)=生",
            "月柱十神流通(藏干): 戊(土)=生 乙(木)=耗 癸(水)=泄",
            "日柱十神流通(干): 干庚(金)=帮",
            "日柱十神流通(支): 支辰(土)=生",
            "日柱十神流通(藏干): 戊(土)=生 乙(木)=耗 癸(水)=泄",
            "时柱十神流通(干): 干丙(火)=克",
            "时柱十神流通(支): 支子(水)=泄",
            "时柱十神流通(藏干): 癸(水)=泄",
            "",
            "【大运】",
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

    def test_cli_yongshen_output(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bazi.main(["1986", "4", "6", "0", "20", "--pretty", "--qiangruo", "--yongshen", "--gender", "男"])
        self.assertEqual(rc, 0)

        out = buf.getvalue().splitlines()
        expected = [
            "【基础】",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 庚辰",
            "时柱: 丙子",
            "",
            "【五行】",
            "日主: 庚金  强弱: 偏弱（韦千里：最弱）",
            "得令: 否 (月令=辰春，金=囚)",
            "得地: 否 (年=绝 日=养 时=死)",
            "同方(帮扶): 金1(囚) 土3(死) => 4 (加权5)",
            "异方(克泄耗): 火3(相) 木3(旺) 水4(休) => 10 (加权39)",
            "用神喜忌: 身弱扶抑：取比劫印为喜，用以扶身；财官为忌，勿再耗克。",
            "喜用五行: 金(囚) 土(死)",
            "忌五行: 木(旺) 火(相)",
        ]
        self.assertEqual(out, expected)

    def test_cli_shishen_flow_and_hechong(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bazi.main(["1986", "4", "6", "0", "20", "--pretty", "--shishen-flow", "--hechong"])
        self.assertEqual(rc, 0)
        out = buf.getvalue().splitlines()
        expected = [
            "【基础】",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 庚辰",
            "时柱: 丙子",
            "",
            "【十神】",
            "年柱十神流通(干): 干丙(火)=克",
            "年柱十神流通(支): 支寅(木)=耗",
            "年柱十神流通(藏干): 甲(木)=耗 丙(火)=克 戊(土)=生",
            "月柱十神流通(干): 干壬(水)=泄",
            "月柱十神流通(支): 支辰(土)=生",
            "月柱十神流通(藏干): 戊(土)=生 乙(木)=耗 癸(水)=泄",
            "日柱十神流通(干): 干庚(金)=帮",
            "日柱十神流通(支): 支辰(土)=生",
            "日柱十神流通(藏干): 戊(土)=生 乙(木)=耗 癸(水)=泄",
            "时柱十神流通(干): 干丙(火)=克",
            "时柱十神流通(支): 支子(水)=泄",
            "时柱十神流通(藏干): 癸(水)=泄",
            "地支合冲刑害破: 月柱-日柱: 支辰∪辰 自刑",
        ]
        self.assertEqual(out, expected)

    def test_cli_liunian_output(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bazi.main(
                ["1986", "4", "6", "0", "20", "--pretty", "--yun", "--liunian", "--liunian-count", "3", "--gender", "男"]
            )
        self.assertEqual(rc, 0)
        out = buf.getvalue().splitlines()
        expected = [
            "【基础】",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 庚辰",
            "时柱: 丙子",
            "",
            "【大运】",
            "起运: 1996-04-21 21:20:00 (顺行, 出生后10年0个月15天21小时，起运虚岁 11)",
            "大运1: 癸巳 (1996-2005, 虚岁11-20)",
            "  流年: 1996丙子(虚岁11) 1997丁丑(虚岁12) 1998戊寅(虚岁13)",
            "大运2: 甲午 (2006-2015, 虚岁21-30)",
            "  流年: 2006丙戌(虚岁21) 2007丁亥(虚岁22) 2008戊子(虚岁23)",
            "大运3: 乙未 (2016-2025, 虚岁31-40)",
            "  流年: 2016丙申(虚岁31) 2017丁酉(虚岁32) 2018戊戌(虚岁33)",
            "大运4: 丙申 (2026-2035, 虚岁41-50)",
            "  流年: 2026丙午(虚岁41) 2027丁未(虚岁42) 2028戊申(虚岁43)",
            "大运5: 丁酉 (2036-2045, 虚岁51-60)",
            "  流年: 2036丙辰(虚岁51) 2037丁巳(虚岁52) 2038戊午(虚岁53)",
            "大运6: 戊戌 (2046-2055, 虚岁61-70)",
            "  流年: 2046丙寅(虚岁61) 2047丁卯(虚岁62) 2048戊辰(虚岁63)",
            "大运7: 己亥 (2056-2065, 虚岁71-80)",
            "  流年: 2056丙子(虚岁71) 2057丁丑(虚岁72) 2058戊寅(虚岁73)",
            "大运8: 庚子 (2066-2075, 虚岁81-90)",
            "  流年: 2066丙戌(虚岁81) 2067丁亥(虚岁82) 2068戊子(虚岁83)",
            "大运9: 辛丑 (2076-2085, 虚岁91-100)",
            "  流年: 2076丙申(虚岁91) 2077丁酉(虚岁92) 2078戊戌(虚岁93)",
        ]
        self.assertEqual(out, expected)

    def test_cli_yun_without_gender_outputs_both(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bazi.main(["1986", "4", "6", "0", "20", "--pretty", "--yun"])
        self.assertEqual(rc, 0)
        out = buf.getvalue().splitlines()
        expected = [
            "【基础】",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 庚辰",
            "时柱: 丙子",
            "",
            "【大运】",
            "男 起运: 1996-04-21 21:20:00 (顺行, 出生后10年0个月15天21小时，起运虚岁 11)",
            "男 大运1: 癸巳 (1996-2005, 虚岁11-20)",
            "男 大运2: 甲午 (2006-2015, 虚岁21-30)",
            "男 大运3: 乙未 (2016-2025, 虚岁31-40)",
            "男 大运4: 丙申 (2026-2035, 虚岁41-50)",
            "男 大运5: 丁酉 (2036-2045, 虚岁51-60)",
            "男 大运6: 戊戌 (2046-2055, 虚岁61-70)",
            "男 大运7: 己亥 (2056-2065, 虚岁71-80)",
            "男 大运8: 庚子 (2066-2075, 虚岁81-90)",
            "男 大运9: 辛丑 (2076-2085, 虚岁91-100)",
            "女 起运: 1986-06-17 03:20:00 (逆行, 出生后0年2个月11天3小时，起运虚岁 1)",
            "女 大运1: 辛卯 (1986-1995, 虚岁1-10)",
            "女 大运2: 庚寅 (1996-2005, 虚岁11-20)",
            "女 大运3: 己丑 (2006-2015, 虚岁21-30)",
            "女 大运4: 戊子 (2016-2025, 虚岁31-40)",
            "女 大运5: 丁亥 (2026-2035, 虚岁41-50)",
            "女 大运6: 丙戌 (2036-2045, 虚岁51-60)",
            "女 大运7: 乙酉 (2046-2055, 虚岁61-70)",
            "女 大运8: 甲申 (2056-2065, 虚岁71-80)",
            "女 大运9: 癸未 (2066-2075, 虚岁81-90)",
        ]
        self.assertEqual(out, expected)

    def test_cli_true_solar_scope_all_changes_pillars(self) -> None:
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
                    "--true-solar",
                    "--true-solar-scope",
                    "all",
                    "--lon",
                    "115.449444",
                    "--lat",
                    "36.490278",
                ]
            )
        self.assertEqual(rc, 0)
        out = buf.getvalue().splitlines()
        expected = [
            "【基础】",
            "真太阳时: 1986-04-05 23:59:00 (lon=115.449444, lat=36.490278)",
            "年柱: 丙寅",
            "月柱: 壬辰",
            "日柱: 己卯",
            "时柱: 丙子",
        ]
        self.assertEqual(out, expected)

    def test_parse_gender_and_invalid_args(self) -> None:
        self.assertEqual(bazi.parse_gender("男"), 1)
        self.assertEqual(bazi.parse_gender("女"), 0)
        self.assertEqual(bazi.parse_gender("male"), 1)
        self.assertEqual(bazi.parse_gender("0"), 0)
        with self.assertRaises(SystemExit):
            bazi.parse_args(["1986", "4", "6", "0", "20", "--true-solar"])


if __name__ == "__main__":
    unittest.main()
