# bazi

输入公历年月日时分，按节气换月/立春换年排八字，可选输出十神、五行生克、强弱/用神、合冲刑害破、起运/大运/流年，支持真太阳时。

## 环境

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## 回归测试

```bash
. .venv/bin/activate
python -m unittest -v
```

## 命令行用法

基本：`python bazi.py YEAR MONTH DAY HOUR MINUTE [--second S]`

常用开关：
- `--pretty` 带字段名输出
- `--shishen` 十神（干+藏干）
- `--shishen-flow` 十神流通（干/支/藏干对日主的生克泄耗帮）
- `--shengke` 五行生克（柱内干支、日主与干支/藏干、生克泄耗帮汇总）
- `--qiangruo` 强弱评估（韦千里：得令/得地/同方异方）
- `--yongshen` 用神喜忌摘要（基于强弱扶抑）
- `--hechong` 干合，支六合/冲/刑/害/破
- `--lunar-info` 农历信息/生肖/节气/月令
- `--hidden-gan` 各支藏干列表
- `--wuxing-count` 五行计数与旺衰标注
- `--changsheng` 长生十二运
- `--nayin` 四柱纳音
- `--kongwang` 旬空
- `--yun` 起运/大运；`--gender 男|女|1|0` 指定性别；`--liunian` 输出流年，`--liunian-count N` 数量
- `--yun-sect 1|2` 起运口径（默认 2 = 分钟数）
- `--true-solar` 真太阳时（需 `--lon` 经度；可配 `--lat` 仅显示）；`--true-solar-scope all|yun` 默认 yun 仅用于起运

不带年月日时分进入交互式输入。

## 示例

```bash
# 基础 + 十神 + 五行生克 + 强弱 + 大运（真太阳时仅用于起运）
.venv/bin/python bazi.py 1986 4 6 0 20 \
  --pretty --shishen --shengke --qiangruo --yun --gender 男 \
  --true-solar --lon 115.449444 --lat 36.490278
```

输出摘录：

```
【基础】
真太阳时(起运用): 1986-04-05 23:59:00 (lon=115.449444, lat=36.490278)
年柱: 丙寅
月柱: 壬辰
日柱: 庚辰
时柱: 丙子

【五行】
…(干支/藏干生克泄耗帮)
日主: 庚金  强弱: 偏弱（韦千里：最弱）
得令: 否 (月令=辰春，金=囚)
得地: 否 (年=绝 日=养 时=死)
同方(帮扶): 金1(囚) 土3(死) => 4 (加权5)
异方(克泄耗): 火3(相) 木3(旺) 水4(休) => 10 (加权39)

【十神】
年柱十神: 干=七杀 支=偏财/七杀/偏印
月柱十神: 干=食神 支=偏印/正财/伤官
日柱十神: 干=日主 支=偏印/正财/伤官
时柱十神: 干=七杀 支=伤官

【大运】
起运: 1996-04-23 14:59:00 (顺行, 出生后10年0个月17天15小时，起运虚岁 11)
大运1: 癸巳 (1996-2005, 虚岁11-20)
…大运9: 辛丑 (2076-2085, 虚岁91-100)
```

更多组合：
- `--shishen-flow --hechong`：十神流通+合冲刑害破
- `--yongshen`：用神喜忌摘要
- `--liunian --liunian-count 5`：每步大运附带 5 个流年
- `--true-solar --true-solar-scope all`：真太阳时用于排盘和起运

说明：输入时间默认按北京时间（UTC+8）。真太阳时需要经度；若仅用于起运请保持 `--true-solar-scope yun`（默认）。未给性别时，大运会同时输出男女两套。
