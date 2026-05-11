# Leon 操作指南 — 10 分钟提交 0G APAC Hackathon

> **目标：** 把 HealthPay Agent 提交到 0G APAC Hackathon  
> **时间：** 10 分钟  
> **截止：** 2026-05-16

---

## 前置准备（5 分钟）

### 1. 获取 0G Testnet Tokens

**为什么需要：** Demo 视频需要展示真实的 0G Storage + Compute 调用

**步骤：**

1. 访问 https://faucet.0g.ai
2. 输入你的钱包地址（从 `.env` 文件中的 `ZG_PRIVATE_KEY` 对应的地址）
3. 点击 "Request Tokens"
4. 等待 1-2 分钟确认

**如果 Faucet 503 错误：**
- 不影响提交，代码已经实现了 graceful degradation
- Demo 视频可以展示 mock mode（deterministic hashes）
- 在提交材料中说明 "Testnet faucet unavailable during development"

### 2. 录制 Demo 视频（可选但推荐）

**时长：** 4-5 分钟  
**脚本：** 参考 `0G_DEMO_SCRIPT.md`

**快速录制方案：**

```bash
# 方案 1：asciinema（终端录制）
asciinema rec demo.cast
# 运行 demo 脚本
python scripts/demo_run.py
# Ctrl+D 结束录制
# 上传到 asciinema.org 获取链接

# 方案 2：OBS Studio（屏幕录制）
# 1. 打开 OBS，添加窗口捕获
# 2. 开始录制
# 3. 运行 demo 脚本
# 4. 停止录制，导出 MP4
# 5. 上传到 YouTube（unlisted）
```

**如果没时间录视频：**
- 不影响提交，Demo 脚本已经写好
- 评委可以根据脚本和代码评估

---

## 提交步骤（5 分钟）

### Step 1: 推代码到 GitHub（2 分钟）

```bash
# 进入项目目录
cd /home/taomi/projects/healthpay-agent

# 确认 .env 文件不会被提交（已在 .gitignore）
cat .gitignore | grep .env

# 初始化 Git（如果还没有）
git init
git add .
git commit -m "HealthPay Agent - 0G APAC Hackathon Submission"

# 创建 GitHub 仓库（在 GitHub 网页上操作）
# 1. 访问 https://github.com/new
# 2. 仓库名：healthpay-agent
# 3. 描述：AI-powered healthcare payment reconciliation on 0G Network
# 4. Public
# 5. 不要勾选 README/LICENSE（我们已经有了）
# 6. Create repository

# 推送代码
git remote add origin https://github.com/YOUR_USERNAME/healthpay-agent.git
git branch -M main
git push -u origin main
```

**检查清单：**
- ✅ README.md 完整（包含 0G 集成说明）
- ✅ 0G_APAC_SUBMISSION.md 存在
- ✅ 0G_DEMO_SCRIPT.md 存在
- ✅ .env 文件未被提交（在 .gitignore 中）
- ✅ requirements.txt 准确
- ✅ LICENSE 文件存在

### Step 2: 提交到 HackQuest（3 分钟）

**平台：** https://hackquest.io/en/hackathon/0g-apac-hackathon

**步骤：**

1. **登录 HackQuest**
   - 使用你的 GitHub 账号登录

2. **找到 0G APAC Hackathon**
   - 点击 "Submit Project"

3. **填写提交表单**

   | 字段 | 内容 |
   |------|------|
   | **Project Name** | HealthPay Agent — Verifiable Healthcare Payment Reconciliation on 0G |
   | **Track** | Verifiable Finance + Agentic Infrastructure |
   | **Tagline** | Turn $262B in healthcare admin waste into verifiable, tamper-proof financial intelligence — powered by 0G Storage + 0G Compute |
   | **Description** | 复制 `0G_APAC_SUBMISSION.md` 的 "Problem Statement" 和 "Solution" 部分 |
   | **GitHub URL** | https://github.com/YOUR_USERNAME/healthpay-agent |
   | **Demo Video** | （如果有）YouTube/asciinema 链接 |
   | **Demo URL** | （可选）如果部署了在线 demo |
   | **Tech Stack** | Python, MCP, FHIR R4, HAPI FHIR, Synthea, 0G Storage, 0G Compute, python-0g, Pydantic, httpx, Docker |
   | **0G Integration** | ✅ 0G Storage (immutable audit trails)<br>✅ 0G Compute (verifiable AI inference) |
   | **Team Members** | Leon Huang (solo) |

4. **上传截图/图片**
   - 架构图（从 `0G_APAC_SUBMISSION.md` 中复制）
   - 终端输出截图（reconciliation 结果 + 0G hash）
   - Financial Vital Signs 截图

5. **提交**
   - 点击 "Submit"
   - 确认收到提交确认邮件

---

## 提交后检查（1 分钟）

### 确认提交成功

- [ ] GitHub 仓库是 Public 的
- [ ] HackQuest 提交页面显示 "Submitted"
- [ ] 收到确认邮件
- [ ] README.md 在 GitHub 上正确渲染

### 可选：分享到社交媒体

**Twitter/X 模板：**

```
Just submitted HealthPay Agent to @0G_labs APAC Hackathon! 🏥💰

Solving the $262B healthcare admin waste problem with:
✅ 0G Storage — Immutable audit trails
✅ 0G Compute — Verifiable AI inference

Built on FHIR R4 + MCP. Production-ready.

GitHub: [YOUR_REPO_URL]
#0GHackathon #VerifiableFinance
```

---

## 常见问题

### Q: 0G Testnet Faucet 一直 503 怎么办？

**A:** 不影响提交。代码已经实现了 graceful degradation：
- 0G Storage → 生成 deterministic mock hashes（`0xMOCK_...`）
- 0G Compute → 自动 fallback 到 OpenAI API

在提交材料中说明：
> "0G testnet faucet was unavailable during development (503 errors). The integration code is complete and tested in mock mode. Production deployment will use mainnet tokens."

### Q: Demo 视频必须录吗？

**A:** 不是必须的，但强烈推荐。如果没时间：
- 提交时在 "Demo Video" 字段填写 "See 0G_DEMO_SCRIPT.md for detailed demo walkthrough"
- 评委可以根据脚本和代码评估

### Q: 需要部署在线 Demo 吗？

**A:** 不需要。HealthPay 是 MCP server，需要 FHIR 数据才能运行。评委可以：
- 克隆仓库
- 运行 `scripts/quickstart.sh`
- 本地测试

### Q: 提交后还能修改吗？

**A:** 取决于 HackQuest 平台规则。通常：
- 提交截止前可以修改
- 提交后可以更新 GitHub 代码（评委会看最新版本）
- 不能修改 HackQuest 表单（除非联系组织者）

### Q: 如果评委问技术问题怎么办？

**A:** 参考这些文档：
- `0G_APAC_SUBMISSION.md` — 完整技术说明
- `src/zero_g_storage.py` — 0G Storage 集成代码
- `src/zero_g_compute.py` — 0G Compute 集成代码
- `scripts/test_0g_integration.py` — 集成测试

---

## 时间线

| 时间 | 任务 | 状态 |
|------|------|------|
| 2026-04-22 | Phase 4 文档完善 | ✅ 完成 |
| 2026-04-23 | 获取 testnet tokens | ⏳ 待做 |
| 2026-04-24 | 录制 demo 视频 | ⏳ 待做 |
| 2026-04-25 | 推代码到 GitHub | ⏳ 待做 |
| 2026-04-25 | 提交到 HackQuest | ⏳ 待做 |
| 2026-05-16 | 提交截止 | 📅 Deadline |

---

## 联系方式

**如果遇到问题：**
- 0G Discord: https://discord.gg/0glabs
- HackQuest Support: support@hackquest.io
- Leon Huang: @leon_huang (Telegram)

---

**Good luck! 🚀**
