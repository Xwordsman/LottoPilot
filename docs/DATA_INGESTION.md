# LottoPilot 开奖数据采集规格

## 1. 数据源原则

默认只采集官方公布的开奖记录：

- 双色球：中国福利彩票发行管理中心，`https://www.cwl.gov.cn/`
- 大乐透：中国体育彩票，`https://www.sporttery.cn/` 及其官方 Web API

第三方站点不得作为默认主数据源。CSV/XLSX 人工导入作为补录方式。

## 2. 双色球适配器

当前可用的官方查询形式示例：

```text
GET https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice
    ?name=ssq
    &pageNo=1
    &pageSize=30
    &systemType=PC
```

需要解析的核心字段：

| 官方字段 | 内部字段 |
|---|---|
| `code` | `issue` |
| `date` | `draw_date` |
| `red` | `primary_numbers` |
| `blue` | `secondary_numbers` |
| `sales` | `sales_amount` |
| `poolmoney` | `pool_amount` |
| `prizegrades` | `prize_tiers` |
| `detailsLink` | `source_detail_url` |

解析规则：红球按逗号拆分成 6 个整数并升序保存；蓝球保存为 1 个整数。

## 3. 大乐透适配器

当前官方查询形式示例：

```text
GET https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry
    ?gameNo=85
    &provinceId=0
    &pageSize=30
    &isVerify=1
    &pageNo=1
```

需要解析的核心字段：

| 官方字段 | 内部字段 |
|---|---|
| `lotteryDrawNum` | `issue` |
| `lotteryDrawTime` | `draw_date` |
| `lotteryDrawResult` | 前 5 个为 `primary_numbers`，后 2 个为 `secondary_numbers` |
| `totalSaleAmount` | `sales_amount` |
| `poolBalanceAfterdraw` | `pool_amount` |
| `prizeLevelList` | `prize_tiers` |
| `drawPdfUrl` | `source_detail_url` |

官方接口有 WAF 和访问频率限制，适配器必须低频调用并带请求间隔、指数退避和随机抖动。

## 4. 统一内部记录

```json
{
  "lottery_type": "ssq",
  "issue": "2026083",
  "draw_date": "2026-07-21",
  "primary_numbers": [7, 14, 15, 23, 28, 33],
  "secondary_numbers": [3],
  "sales_amount": "348240258",
  "pool_amount": "480802779",
  "prize_tiers": [],
  "source_name": "cwl_official",
  "source_url": "https://www.cwl.gov.cn/...",
  "source_fetched_at": "2026-07-23T08:00:00+08:00"
}
```

金额使用 Decimal 或原始字符串解析，禁止使用浮点数保存货币。

## 5. 校验规则

### 双色球

- `primary_numbers` 长度为 6，互不重复，范围 1–33。
- `secondary_numbers` 长度为 1，范围 1–16。
- 期号只包含数字，日期可解析。

### 大乐透

- `primary_numbers` 长度为 5，互不重复，范围 1–35。
- `secondary_numbers` 长度为 2，互不重复，范围 1–12。
- 期号只包含数字，日期可解析。

### 通用

- 数组进入数据库前升序排序。
- 唯一键是 `(lottery_type, issue)`。
- 同期数据变化时更新记录并写审计日志。
- 对每期规范化后的原始 item JSON 计算 SHA-256，写入 `source_hash`，便于精确识别单期开奖源数据变化。
- 校验失败的数据进入 ingestion error，不写入正式开奖记录表。

## 6. 同步策略

### 首次全量同步

1. 从第一页开始分页。
2. 每页解析、校验、批量 upsert。
3. 页面之间等待 1–3 秒随机间隔。
4. 保存同步游标、页码和统计。
5. 任务中断后从最近成功页恢复。

### 增量同步

1. 读取数据库最新期号。
2. 请求官方最新 10–30 期。
3. 从最新期向后处理，遇到已存在且哈希相同的期号后停止。
4. 新数据写入后触发推荐归档复盘和统计快照刷新。

### 调度建议

- 双色球开奖日：周二、周四、周日晚上低频轮询。
- 大乐透开奖日：周一、周三、周六晚上低频轮询。
- 具体开始时间做成设置项；默认每 15 分钟检查一次，发现新期后停止本晚轮询。
- 每天凌晨执行一次轻量补漏同步。

## 7. HTTP 策略

- 使用统一 `httpx.AsyncClient`。
- 设置合理的连接、读取和总超时。
- User-Agent、Referer 和 Accept 在适配器中明确配置。
- 429、5xx、网络中断使用指数退避。
- WAF 拦截页面按采集失败记录，不尝试高频绕过。
- 每个官方域名单独限速。
- 保存最后成功时间、连续失败次数和下次重试时间。

## 8. CSV/XLSX 导入

支持字段映射和预览，最低要求字段：

```text
lottery_type, issue, draw_date, primary_numbers, secondary_numbers
```

号码字段支持：

```text
01,02,03,04,05,06
01 02 03 04 05 06
[1,2,3,4,5,6]
```

导入流程：上传、字段识别、预览、逐行校验、确认、批量 upsert、生成导入报告。

## 9. 测试要求

- 每个官方适配器保存脱敏 JSON fixture。
- Parser 测试不得依赖实时网络。
- 增加字段缺失、空列表、WAF HTML、乱码、重复期号和非法号码测试。
- 网络 smoke test 单独标记，默认 CI 不执行实时官方请求。
