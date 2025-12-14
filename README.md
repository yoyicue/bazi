# bazi

输入公历年月日和小时分钟，输出八字（年柱 月柱 日柱 时柱）。

## 环境搭建

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

## 使用

```bash
python bazi.py 2025 12 14 12 0
python bazi.py 2025 12 14 12 0 --pretty
python bazi.py 2025 12 14 12 0 --pretty --shishen
python bazi.py 2025 12 14 12 0 --pretty --qiangruo
python bazi.py 1986 4 6 0 20 --pretty --yun --gender 男
python bazi.py 1986 4 6 0 20 --pretty --yun  # 未指定性别则输出男/女两套
python bazi.py 1986 4 6 0 20 --pretty --yun --gender 男 --true-solar --lon "E115°26'58\"" --lat "N36°29'25\""
python bazi.py  # 交互式输入
python bazi.py --shishen  # 交互式输入并输出十神
python bazi.py --yun --gender 女  # 交互式输入并输出起运/大运
```

说明：默认按“节气换月、立春换年”的四柱八字口径计算；输入时间按北京时间（UTC+8）理解；`--true-solar` 默认仅用于起运/大运（因此需配合 `--yun` 使用），若需用于排盘可加 `--true-solar-scope all`。
