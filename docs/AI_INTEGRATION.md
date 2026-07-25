# LottoPilot AI 集成规格

## 1. 定位

AI 是统计引擎的辅助层，负责：

- 对统计候选池进行受限二次排序。
- 将特征摘要转成易读说明。
- 生成当期分析摘要。
- 回测报告总结和异常提示。

AI 不负责绕过号码规则，也不直接访问数据库或官方采集接口。

## 2. 协议

首版统一使用 OpenAI-compatible Chat Completions 接口，并封装内部 client，避免业务代码依赖具体 SDK。后续增加 Responses 风格适配器时必须继续实现同一个内部协议。

```python
class LLMClient(Protocol):
    async def test_connection(self) -> ModelInfo: ...
    async def rerank_candidates(self, request: RerankRequest) -> RerankResponse: ...
    async def explain_tickets(self, request: ExplainRequest) -> ExplainResponse: ...
```

支持示例：OpenAI、DeepSeek、通义兼容端点、SiliconFlow、New API、自建 OpenAI 兼容网关和 Ollama。

## 3. 配置项

- 配置名称。
- Provider 类型。
- Base URL。
- API Key。
- 模型名。
- Temperature，默认 0.2。
- Timeout，默认 60 秒。
- 最大输出 token。
- 是否启用候选重排。
- 是否启用解释。
- 是否为默认配置。

前端提供“测试连接”按钮。测试结果只返回模型、延迟和状态，不返回 Key。

## 4. 密钥管理

- `APP_SECRET` 从环境变量读取，至少 32 字节随机值。
- 使用 HKDF 从 `APP_SECRET` 派生 AES-256-GCM key。
- 每次加密使用随机 nonce，并保存版本、nonce、ciphertext 和 tag。
- API 响应只返回 `has_api_key` 和掩码，例如 `sk-****8f32`。
- 更新时空 Key 表示保留原 Key，显式 `clear_api_key=true` 才删除。
- 日志、审计 metadata、异常堆栈和前端状态中不得出现完整 Key。
- 支持 `LLM_API_KEY` 环境变量作为只读默认值；数据库配置优先级在文档和 UI 中明确显示。

## 5. AI 输入压缩

不发送完整历史开奖列表。后端先构建紧凑输入：

```json
{
  "lottery_type": "ssq",
  "target_issue": "2026084",
  "data_cutoff": "2026083",
  "summary": {
    "window_sizes": [30, 60, 120],
    "frequency_ranks": {},
    "omission_ranks": {},
    "structure_percentiles": {}
  },
  "candidates": [
    {
      "id": "c_001",
      "primary": [1, 7, 14, 18, 26, 31],
      "secondary": [9],
      "statistical_score": 83.42,
      "features": {
        "sum_percentile": 0.54,
        "span_percentile": 0.61,
        "odd_even": "3:3",
        "zones": "2:2:2"
      }
    }
  ]
}
```

候选数量默认 30，最大 50。请求体大小设置硬上限。

## 6. 结构化输出

AI 必须返回 JSON：

```json
{
  "rankings": [
    {
      "candidate_id": "c_001",
      "score": 82,
      "tags": ["三区均衡", "和值中位"],
      "reason": "结构位于近期主要分布区间，窗口表现相对稳定。"
    }
  ],
  "summary": "本期候选侧重结构分散和跨窗口稳定性。"
}
```

后端校验：

- `candidate_id` 必须来自输入。
- ID 不得重复。
- score 范围 0–100。
- 标签数量、长度和 reason 长度受限。
- 输出不得包含输入之外的新号码。
- 缺失候选使用统计排名补齐。

## 7. 提示词原则

System prompt 必须包含：

1. 这是候选排序与解释任务。
2. 所有合法组合理论中奖概率相同。
3. 仅使用提供的统计摘要。
4. 仅返回约定 JSON。
5. 禁止新增、删除或修改候选号码。
6. 解释使用“模型评分、结构、稳定性”等措辞。

提示词要有版本号，例如 `rerank-v1`、`explain-v1`，版本写入推荐运行记录。

## 8. 最终分融合

AI 权重默认 0.10，后端上限 0.10：

```text
final_score = stat_score * (1 - ai_weight) + ai_score * ai_weight
```

AI 调用失败、超时或输出校验失败时：

- `ai_status=failed`。
- 保存错误类别和耗时，不保存敏感响应头。
- 最终顺序使用统计分。
- 页面展示“统计结果已生成，AI 说明本次未完成”。

## 9. 成本控制

- 只发送 Top 30–50 候选。
- 相同数据快照、策略版本、候选哈希、模型和 prompt 版本可缓存响应。
- 显示估算输入/输出 token 和耗时。
- 设置单次最大 token、每日调用次数和并发限制。
- “重新生成解释”与“重新生成候选”是两个独立操作。

## 10. 测试

- 使用 fake LLM client 测试正常、超时、非法 JSON、重复 ID、越界 score 和未知 ID。
- 测试 Key 加密解密和 APP_SECRET 错误场景。
- 测试 API 响应和日志不泄露 Key。
- 真实供应商连接测试标记为 manual，不进入普通 PR CI。
