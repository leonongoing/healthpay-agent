# Kaggle 提交清单 — HealthPay Agent
**截止：2026-05-18 23:59 UTC（北京时间 5/19 07:59）**
**预计 Leon 操作时间：30 分钟**

---

## 第一步：推 GitHub（10 分钟）

```bash
# 在本机执行（或让大富翁帮你推）
cd /home/taomi/projects/healthpay-agent

# 确认 .gitignore 包含 .env（不要泄露 API Key）
cat .gitignore | grep .env

# 推到 public repo
git add -A
git commit -m "feat: Gemma 4 Good Hackathon submission - HealthPay Agent"
git push origin main
```

**GitHub Repo URL（需要是 public）：**
- 如果还没有 repo，在 github.com 新建：`healthpay-agent`
- 推完后记录 URL：`https://github.com/leonongoing/healthpay-agent`

---

## 第二步：Kaggle 账号配置（5 分钟）

1. 登录 https://www.kaggle.com（用 leonongoing@gmail.com）
2. 进入 Settings > Secrets
3. 添加 Secret：
   - Name: `GEMINI_API_KEY`
   - Value: `AIzaSyBLgYufRMHIm4miORVz-8nss8HEPETIwsk`

---

## 第三步：上传 Notebook（10 分钟）

1. 进入 https://www.kaggle.com/code
2. 点击 **New Notebook**
3. 点击 **File > Import Notebook**
4. 上传 `kaggle_notebook.ipynb`（位于项目根目录）
5. 点击 **Run All**，确认所有 cell 运行成功
6. 点击 **Save Version** > **Save & Run All (Commit)**
7. 记录 Notebook URL

---

## 第四步：Kaggle 竞赛提交（5 分钟）

1. 进入竞赛页面：https://www.kaggle.com/competitions/gemma-4-good
2. 点击 **Submit**
3. 填写：
   - **Title:** HealthPay Agent: AI-Powered Healthcare Payment Reconciliation
   - **Summary:** Gemma 4-powered MCP server for FHIR R4 healthcare payment intelligence. Reduces $262B annual administrative waste through AI denial analysis, A/R optimization, and compliance checking.
   - **GitHub URL:** （第一步的 repo URL）
   - **Notebook URL:** （第三步的 notebook URL）
   - **Track:** Health & Sciences
4. 提交

---

## 提交材料清单

| 材料 | 状态 | 位置 |
|------|------|------|
| Write-up (≤1500 字) | ✅ 完成 (1375 字) | `docs/kaggle-writeup.md` |
| GitHub 代码仓库 | ⏳ 需要 Leon push | - |
| Kaggle Notebook | ✅ 完成 | `kaggle_notebook.ipynb` |
| Demo 视频脚本 | ✅ 完成 | `docs/demo-video-script.md` |
| Demo 视频 (≤3 分钟) | ⏳ 需要 Leon 录制 | - |

---

## 视频录制要点（3 分钟内）

**工具：** OBS / QuickTime / 手机录屏均可

**脚本（按顺序）：**
1. **0:00-0:30** — 问题陈述："每年 $262B 浪费在医疗账单行政工作上"
2. **0:30-1:00** — 运行 Kaggle Notebook，展示 Demo 1（Denial Analysis）
3. **1:00-1:45** — 展示 Demo 2（A/R Financial Vital Signs）
4. **1:45-2:15** — 展示 Demo 3（Compliance Check）
5. **2:15-2:45** — 架构图（README 里有）+ Gemma 4 差异化
6. **2:45-3:00** — Impact：帮助小诊所每月多回收 $15K+

**上传到：** YouTube（unlisted）或 Google Drive，提交时填 URL

---

## 紧急联系

如果遇到问题，找大富翁：
- Gemma 4 API 报错 → 检查 `.env` 里的 `GEMINI_API_KEY`
- Kaggle 提交报错 → 截图发给大富翁

---

_大富翁出品 | 2026-05-14 18:xx_
