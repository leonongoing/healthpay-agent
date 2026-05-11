# Gemma 4 Integration Plan — HealthPay Agent

> Hackathon: **Gemma 4 Good** ($200K, Google DeepMind + Kaggle)
> Deadline: **May 18, 2026, 23:59 UTC**
> Track: **Health & Sciences** ($10K track prize + main prizes up to $50K)

---

## 1. 竞赛要求摘要

### 提交物
| 项目 | 要求 |
|------|------|
| Write-up | ≤1500 字技术报告，说明架构和 Gemma 4 使用方式 |
| Code Repo | 公开 GitHub/Kaggle Notebook，文档完善 |
| Demo | 可运行的 demo 或 demo 文件 |
| Video | ≤3 分钟 YouTube 视频 |
| Cover Image | 项目封面图 |

### 评分标准
- **Impact & Vision** (40分): 解决真实问题的能力
- **Video Pitch** (30分): 视频质量和叙事
- **Technical Depth** (30分): Gemma 4 技术深度和创新

### 关键规则
- 必须使用 Gemma 4 模型家族
- 鼓励 post-training、domain adaptation、agentic retrieval
- Apache 2.0 开源许可

---

## 2. Gemma 4 模型规格

| 模型 | 参数量 | 架构 | 上下文 | 适用场景 |
|------|--------|------|--------|----------|
| **Gemma 4 E2B** | ~2B effective | Dense | 32K | 边缘设备、移动端 |
| **Gemma 4 E4B** | ~4B effective | Dense | 128K | 轻量级推理 |
| **Gemma 4 26B (MoE)** | 26B total / 3.8B active | MoE | 256K | ⭐ **推荐** — 性价比最高 |
| **Gemma 4 31B** | 31B | Dense | 256K | 最高质量 |

### 关键能力
- 多模态：文本 + 图像输入（小模型支持音频）
- 140+ 语言支持
- 高级推理和 agentic workflows
- Thinking mode（类似 chain-of-thought）

---

## 3. 集成方案评估

### 方案 A: Google AI Studio API（⭐ 推荐）

**方式**: 通过 Gemini API 调用 Gemma 4，使用 `google-genai` Python SDK

```python
from google import genai

client = genai.Client(api_key="GEMINI_API_KEY")
response = client.models.generate_content(
    model="gemma-4-27b-it",  # 或 gemma-4-26b-a4b-it
    contents="Analyze this medical claim...",
    config={"temperature": 0.3, "max_output_tokens": 2048}
)
```

| 维度 | 评分 |
|------|------|
| 成本 | ✅ 免费（有 rate limit） |
| 速度 | ✅ 快（云端 GPU） |
| 易用性 | ✅ 最简单，pip install 即可 |
| Kaggle 合规 | ✅ 完全合规（Google 官方） |
| 可靠性 | ✅ Google 基础设施 |

**优势**: 零成本、零运维、最快集成、Kaggle 官方推荐
**劣势**: 依赖网络、有 rate limit（免费 tier: 15 RPM / 1M TPM）

### 方案 B: Hugging Face Transformers（本地推理）

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("google/gemma-4-27b-it")
```

| 维度 | 评分 |
|------|------|
| 成本 | ❌ 需要 GPU（A100 80GB for 27B） |
| 速度 | ⚠️ 取决于硬件 |
| 易用性 | ⚠️ 需要 GPU 环境配置 |
| Kaggle 合规 | ✅ 合规 |
| 可靠性 | ✅ 本地运行 |

**优势**: 完全离线、无 rate limit
**劣势**: 需要昂贵 GPU、部署复杂、我们服务器只有 8GB RAM 无 GPU

### 方案 C: Ollama（本地推理）

```bash
ollama pull gemma4:12b  # ~7.2GB
ollama run gemma4:12b
```

| 维度 | 评分 |
|------|------|
| 成本 | ⚠️ 需要 16GB+ RAM |
| 速度 | ⚠️ CPU 推理很慢 |
| 易用性 | ✅ 简单 |
| Kaggle 合规 | ✅ 合规 |
| 可靠性 | ✅ 本地运行 |

**优势**: 简单部署、OpenAI 兼容 API
**劣势**: 我们服务器 8GB RAM 不够跑 12B+、CPU 推理太慢

### 方案 D: Kaggle Notebook（免费 GPU）

在 Kaggle Notebook 中运行，使用免费 T4/P100 GPU。

| 维度 | 评分 |
|------|------|
| 成本 | ✅ 免费 |
| 速度 | ⚠️ 中等 |
| 易用性 | ⚠️ 需要适配 Notebook 环境 |
| Kaggle 合规 | ✅ 最合规 |
| 可靠性 | ⚠️ 有时间限制 |

**优势**: 免费 GPU、Kaggle 原生
**劣势**: 不适合做 production demo、有运行时间限制

### 方案对比总结

| 方案 | 成本 | 速度 | 易用性 | 合规性 | 总分 |
|------|------|------|--------|--------|------|
| **A: Google AI Studio** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | **12/12** |
| B: HuggingFace | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | 7/12 |
| C: Ollama | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 8/12 |
| D: Kaggle Notebook | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | 10/12 |

### ✅ 推荐方案: A (Google AI Studio API) + D (Kaggle Notebook 作为 demo)

- **开发和 Demo**: 使用 Google AI Studio API（`google-genai` SDK）
- **Kaggle 提交**: 同时提供 Kaggle Notebook 版本
- **Fallback**: 保留 OpenAI 作为降级方案

---

## 4. 代码改动清单

### 4.1 核心改动（必须）

#### `src/config.py` — 添加 Gemma 4 配置
```python
# 新增配置项
gemma4_api_key: Optional[str] = None          # GEMINI_API_KEY
gemma4_model: str = "gemma-4-27b-it"          # 默认模型
gemma4_temperature: float = 0.3               # 医疗场景用低温度
gemma4_max_tokens: int = 4096                 # 最大输出 token
llm_provider: str = "gemma4"                  # gemma4 | openai | 0g
```

#### `src/gemma4_client.py` — 新建 Gemma 4 客户端（替代 zero_g_compute.py）
```python
"""
Gemma 4 LLM Client via Google AI Studio (Gemini API).
Drop-in replacement for ZeroGLLM with OpenAI-compatible interface.
"""
from google import genai

class Gemma4LLM:
    def __init__(self, api_key, model="gemma-4-27b-it"):
        self.client = genai.Client(api_key=api_key)
        self.model = model
    
    async def chat_completion(self, messages, temperature=0.3, max_tokens=4096):
        # Convert OpenAI message format to Gemini format
        contents = self._convert_messages(messages)
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config={"temperature": temperature, "max_output_tokens": max_tokens}
        )
        return self._to_openai_format(response)
```

#### `src/zero_g_compute.py` — 修改 fallback 链
```
当前: 0G Compute → OpenAI
改为: Gemma 4 (Google AI Studio) → 0G Compute → OpenAI
```

### 4.2 增强改动（加分项）

#### 新增: `src/gemma4_healthcare_prompts.py`
- 医疗领域专用 prompt templates
- 利用 Gemma 4 的 thinking mode 做复杂推理
- 结构化输出（JSON mode）

#### 新增: `notebooks/gemma4_healthpay_demo.ipynb`
- Kaggle Notebook 格式的完整 demo
- 展示所有 6 个 MCP tools 的 Gemma 4 驱动版本

#### 修改: `src/denial_analyzer.py`
- 当前: 纯规则引擎（CARC code mapping）
- 增强: 用 Gemma 4 做自然语言拒付原因分析
- 增强: 用 Gemma 4 生成个性化 appeal letter

#### 修改: `src/ar_reporter.py`
- 增强: 用 Gemma 4 生成自然语言财务分析报告
- 增强: 用 Gemma 4 做趋势预测和建议

### 4.3 文件改动汇总

| 文件 | 操作 | 工作量 |
|------|------|--------|
| `src/config.py` | 修改 | 0.5h |
| `src/gemma4_client.py` | 新建 | 2h |
| `src/gemma4_healthcare_prompts.py` | 新建 | 2h |
| `src/zero_g_compute.py` | 修改 | 1h |
| `src/denial_analyzer.py` | 增强 | 2h |
| `src/ar_reporter.py` | 增强 | 1.5h |
| `src/mcp_server.py` | 微调 | 0.5h |
| `scripts/test_gemma4_integration.py` | 新建 | ✅ 已完成 |
| `notebooks/gemma4_healthpay_demo.ipynb` | 新建 | 3h |
| `.env.example` | 更新 | 0.5h |
| `README.md` | 更新 | 1h |
| `requirements.txt` | 更新 | 0.5h |

---

## 5. Gemma 4 vs OpenAI 性能对比（预估）

基于 Gemma 4 公开 benchmark 和 HealthPay 任务特点：

| 任务 | OpenAI (GPT-4o-mini) | Gemma 4 (27B) | 评估 |
|------|---------------------|---------------|------|
| 医疗账单对账分析 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 持平 — 结构化数据分析 |
| 拒付原因分类 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Gemma 4 略弱 — 需要 domain prompt |
| 财务报告生成 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 持平 — 数据汇总任务 |
| JSON 结构化输出 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Gemma 4 需要更强的 prompt |
| 推理速度 (API) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 持平 |
| 成本 | ⭐⭐⭐ (付费) | ⭐⭐⭐⭐⭐ (免费) | Gemma 4 胜 |
| 上下文窗口 | 128K | 256K | Gemma 4 胜 |

### 关键差异
- **Gemma 4 优势**: 免费、256K 上下文、thinking mode、开源
- **OpenAI 优势**: JSON mode 更稳定、function calling 更成熟
- **结论**: Gemma 4 完全可以胜任 HealthPay 的所有任务，需要优化 prompt engineering

---

## 6. 开发计划

### Phase 1: 基础集成（1 天）
- [x] 研究 Gemma 4 模型和竞赛规则
- [x] 评估集成方案
- [x] 编写测试脚本
- [ ] 获取 Gemini API Key
- [ ] 运行测试验证

### Phase 2: 核心替换（1.5 天）
- [ ] 创建 `gemma4_client.py`
- [ ] 修改 `config.py` 添加 Gemma 4 配置
- [ ] 修改 `zero_g_compute.py` fallback 链
- [ ] 编写医疗领域 prompt templates
- [ ] 端到端测试所有 MCP tools

### Phase 3: 增强功能（1.5 天）
- [ ] 用 Gemma 4 增强 denial_analyzer（自然语言分析 + appeal letter）
- [ ] 用 Gemma 4 增强 ar_reporter（自然语言报告）
- [ ] 利用 thinking mode 做复杂推理
- [ ] 性能优化和 prompt 调优

### Phase 4: 提交准备（1 天）
- [ ] 创建 Kaggle Notebook demo
- [ ] 录制 3 分钟 demo 视频
- [ ] 撰写 1500 字技术 write-up
- [ ] 准备 GitHub repo（公开、文档完善）
- [ ] 制作封面图

### 总预估: 5 天

---

## 7. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Gemma 4 API rate limit 不够 | 低 | 中 | 免费 tier 15 RPM 足够 demo |
| Gemma 4 JSON 输出不稳定 | 中 | 中 | 强化 prompt + 输出解析容错 |
| Gemma 4 医疗领域知识不足 | 低 | 高 | 用 few-shot examples + domain prompts |
| API key 获取困难 | 低 | 高 | Google AI Studio 免费注册即可 |
| 网络访问问题（中国大陆） | 中 | 中 | 使用代理 http://127.0.0.1:7897 |
| 竞争激烈 | 高 | 中 | 聚焦 Health track，突出 FHIR + 0G 差异化 |

---

## 8. 竞争优势分析

### HealthPay 的差异化
1. **真实医疗场景**: 不是 toy demo，是解决 $262B 行政浪费的实际工具
2. **FHIR R4 标准**: 可对接任何 EHR 系统
3. **0G 去中心化审计**: 不可篡改的审计追踪（区块链 + AI 结合）
4. **MCP 协议**: 标准化 AI Agent 接口
5. **Gemma 4 深度集成**: thinking mode + 256K 上下文处理大量医疗数据

### 建议参赛 Track
- **主 Track**: Health & Sciences（$10K track prize）
- **技术亮点**: Gemma 4 thinking mode 用于复杂医疗推理

---

## 9. 快速启动指南

```bash
# 1. 获取 API Key
# 访问 https://aistudio.google.com/apikey

# 2. 设置环境变量
export GEMINI_API_KEY="your_key_here"

# 3. 安装依赖
pip install google-genai

# 4. 运行测试
cd /home/taomi/projects/healthpay-agent
python scripts/test_gemma4_integration.py

# 5. 查看结果
cat /tmp/gemma4_test_results.json
```

---

## 10. 下一步行动

1. **立即**: Leon 获取 Gemini API Key（https://aistudio.google.com/apikey）
2. **立即**: 运行 `scripts/test_gemma4_integration.py` 验证 Gemma 4 可用性
3. **确认后**: 开始 Phase 2 核心替换开发
4. **5月10日前**: 完成所有开发，留一周做提交准备

---

*文档生成时间: 2026-04-19*
*作者: 鲁班 (AI Engineer)*
