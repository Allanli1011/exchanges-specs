# Global Futures Contract Specification Collector

全球期货合约规格采集系统，覆盖22个交易所。当前版本对部分交易所使用官方实时源或官方文件补充，最新全量导出样本为 488 条合约记录，输出为带质量标签和来源元数据的 Excel 工作簿。

## Latest Status

- Latest full export: `Global_Futures_Specs_ALL_2026-03-24_17-43-28.xlsx`
- Total contracts: `488`
- Source types: `static=206`, `csv+html=211`, `api=20`, `api+static=51`
- Official live-source exchanges now include `NSE` (official CSV), `SHFE` (official APIs), and `CME` (official product catalog + Contract Specs APIs)
- Current data-quality distribution: `partial=282`, `manual_review=206`

## 覆盖范围

| 地区 | 交易所 | 合约数 |
|------|--------|--------|
| 北美 | CME, CBOT, NYMEX, COMEX | 51 |
| 北美 | ICE Futures US | 8 |
| 北美 | ICE Futures Europe | 10 |
| 北美 | CBOE Futures | 4 |
| 欧洲 | Eurex | 16 |
| 欧洲 | LME (伦敦金属交易所) | 15 |
| 亚太 | SGX (新加坡) | 9 |
| 亚太 | HKEX (香港) | 10 |
| 亚太 | JPX / OSE / TOCOM (日本) | 18 |
| 亚太 | KRX (韩国) | 10 |
| 亚太 | TAIFEX (台湾) | 8 |
| 亚太 | BMD (马来西亚) | 8 |
| 亚太 | ASX (澳大利亚) | 9 |
| 亚太 | NSE (印度) | 216 |
| 中国 | SHFE (上期所) | 20 |
| 中国 | DCE (大商所) | 20 |
| 中国 | CZCE (郑商所) | 22 |
| 中国 | CFFEX (中金所) | 8 |
| 中国 | INE (上期能源) | 4 |
| 中国 | GFEX (广期所) | 2 |
| 美洲 | B3 (巴西) | 10 |
| 欧洲 | MOEX (莫斯科) | 10 |

说明：上表表示最近一次全量导出的记录数；其中使用官方 CSV/API/HTML 动态发现的交易所，数量会随官方目录变化而变化。

## 数据字段（40+ schema，实际覆盖度因交易所而异）

### 基础规格
交易所、品种名（中英文）、代码、合约大小、报价单位、货币、最小变动价位、Tick值、合约月份、交易时间

### TAS/TAM 规则
TAS是否可用、TAS允许的tick范围、TAS可交易月份、TAM规则、BTIC规则、大宗交易最低限额

### 风控限制
涨跌停板、价格限制类型、初始保证金、维持保证金、持仓限制（现货月/单月/所有月份）、大户报告水平

### 交割规则
交割方式（实物/现金）、最后交易日、首次通知日、交割品级、交割地点、最终结算价计算方式

## 安装

```bash
pip install -r requirements.txt
```

依赖：
- `httpx` — 异步HTTP客户端
- `beautifulsoup4` + `lxml` — HTML解析
- `openpyxl` — Excel生成
- `pydantic` — 数据模型验证
- `pyyaml` — 配置文件
- `tenacity` — HTTP重试
- `tqdm` — 进度条
- `aiosqlite` — HTTP响应缓存

## 使用

```bash
# 采集全部交易所
python -m src.main --exchanges all

# 只采集指定交易所
python -m src.main --exchanges CME SHFE EUREX LME

# 不使用缓存（强制重新获取）
python -m src.main --exchanges all --no-cache

# 自定义缓存有效期（秒）
python -m src.main --exchanges all --cache-ttl 3600

# 调整并发数
python -m src.main --exchanges all --parallel 3

# 详细日志
python -m src.main --exchanges all -v
```

输出文件位于 `data/output/Global_Futures_Specs_{范围}_{时间戳}.xlsx`，例如 `Global_Futures_Specs_ALL_2026-03-24_17-43-28.xlsx`。

## Excel 输出结构

| Sheet | 内容 |
|-------|------|
| **Summary** | 仪表板：各交易所合约数量、数据完整度、更新时间 |
| **All Contracts** | 全部合约主表，包含质量标签、来源类型、来源URL、备注 |
| **{交易所名}** | 每个交易所一个独立Sheet |
| **TAS-TAM Rules** | TAS/TAM/BTIC专题汇总 |
| **Risk Controls** | 保证金、持仓限制、涨跌停 |
| **Delivery Specs** | 交割方式、日期、品级、地点 |
| **Data Quality** | 数据来源URL、采集时间、完整度评分、质量标签、备注 |

## 项目结构

```
├── config/
│   └── exchanges.yaml          # 交易所注册表（URL、限速配置）
├── src/
│   ├── main.py                 # CLI入口
│   ├── models/
│   │   └── contract_spec.py    # Pydantic统一数据模型
│   ├── collectors/             # 每个交易所一个采集器
│   │   ├── base.py             # 抽象基类
│   │   ├── cme_group.py        # CME/CBOT/NYMEX/COMEX
│   │   ├── shfe.py             # 上期所
│   │   ├── ...                 # 其余20个交易所
│   ├── parsers/
│   │   └── html_parser.py      # HTML表格解析工具
│   ├── exporters/
│   │   └── excel_exporter.py   # Excel生成（openpyxl）
│   └── utils/
│       ├── http_client.py      # 异步HTTP（重试+限速+缓存）
│       └── cache.py            # SQLite响应缓存
├── data/
│   ├── cache/                  # HTTP缓存（自动生成）
│   └── output/                 # Excel输出
└── requirements.txt
```

## 技术特性

- **异步并发**：基于 `httpx` + `asyncio`，跨交易所并行采集（默认5路并发）
- **智能缓存**：SQLite缓存HTTP响应，默认24小时有效，避免重复请求
- **错误隔离**：单个交易所采集失败不影响其他交易所
- **速率限制**：按域名独立限速，防止被交易所网站封禁
- **官方源增强**：`NSE` 使用官方 CSV，`SHFE` 使用官方 API，`CME` 使用官方产品目录与 Contract Specs API 补全关键字段
- **注册表生效**：`config/exchanges.yaml` 现在参与运行时校验与区域映射
- **重复防护**：导出前会去重，并在采集器返回越界交易所代码时直接报错
- **数据质量**：自动计算完整度，并推断 `complete / partial / manual_review`

## 扩展新交易所

1. 在 `src/collectors/` 下新建文件，继承 `BaseCollector`
2. 实现 `collect_all()` 方法，返回 `List[ContractSpec]`
3. 在 `src/main.py` 的 `COLLECTOR_MAP` 中注册
4. 在 `config/exchanges.yaml` 中添加配置

```python
# src/collectors/new_exchange.py
from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec

class NewExchangeCollector(BaseCollector):
    exchange_code = "NEW"
    exchange_name_en = "New Exchange"

    async def collect_all(self) -> list[ContractSpec]:
        # 实现采集逻辑
        ...
```

## License

MIT
