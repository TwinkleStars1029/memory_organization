# Offline RPG Memory Distillation Skill

> 將長篇 AI-RPG 對話紀錄離線蒸餾成「可驗證的記憶卡 YAML」，無需付費 API。  
> Python 負責解析 / 切片與骨架生成；Codex（VS Code）負責語意摘要與記憶整理。

## ✨ Features

- ✅ **完全離線 / 無付費 API**
- ✅ **彈性 Schema（Single Source of Truth）**
  - `schema.yaml` 定義所有記憶欄位與驗證規則
  - `split.py` / `verify.py` 讀取 schema，不硬編欄位
- ✅ 以「chunk → memory card」的方式穩定處理超長對話
- ✅ 內建驗證流程，避免亂填 / schema drift / hallucination

## 📦 Repo Structure
```
input/
  raw_chat.txt               # 原始對話紀錄（你要放的檔案）

chunks/
  ch_0001.txt                # split.py 產生的對話切片
  ch_0002.txt
  ...

output/
  chapters/
    ch_0001.yaml             # 對應 chunk 的記憶卡 YAML skeleton
    ch_0002.yaml
    ...

schema.yaml                  # 記憶 schema（唯一真實來源）
MemoryTemplate.txt           # Codex distillation 填寫規則
split.py                     # 切片 + skeleton 生成（讀取 schema.yaml）
verify.py                    # 依 schema 驗證 output YAML（讀取 schema.yaml）
SKILL.md
```

## 🚀 Quick Start
### 1) 放入對話紀錄
把你的 AI-RPG 對話 log 放在input資料夾中，重新命名為`raw_chat.txt`：
- `input/raw_chat.txt`

### 2) 執行指令產生記憶體
在IDE介面中的codex或gemini視窗，執行以下指令，會先產生5筆記憶體於目錄下
```bash
請閱讀並遵守本專案的 @SKILL.md 、 @MemoryTemplate.txt 。 你現在是 RPG 記憶檔案管理員。

Step 0 — 準備切片 確認 input/raw_chat.txt 存在且非空。 在終端機執行：python split.py 確認已產生 chunks/ch_0001.txt（以及 output/chapters/ch_0001.yaml skeleton）。

Step 1 — 寫入記憶卡（本輪 10 份） 依照 MemoryTemplate.txt、schema.yaml 規則，將下列檔案逐一整理成記憶卡並填入同名 YAML（只修改既有欄位，不新增欄位、不臆測）： chunks/ch_0001.txt → output/chapters/ch_0001.yaml … chunks/ch_0010.txt → output/chapters/ch_0010.yaml

Step 2 — 驗收 完成後在終端機執行：python verify.py，並貼出結果。 若有錯誤或缺漏，請指出是哪個檔案與原因。

```

### 3) 自動化生產記憶體
確認產出記憶無誤後，在codex或gemini視窗，接續執行以下指令
```bash
我已完成並驗證前 10 份章節（ch_0001 ~ ch_0010）。接下來請你「完全不要停下來詢問是否繼續」，從「目前已完成的最後章節」開始接續處理（以 output/chapters/ch_XXXX.yaml 的編號為準），直接用相同規則依序處理 chunks 直到最後一個 chunk
```

---

## AI Flow說明

### 1) 放入對話紀錄

把你的 AI-RPG 對話 log 放在：

- `input/raw_chat.txt`

### 2) 切片 + 生成記憶 skeleton

在終端機執行：

```bash
python split.py
```

你應該會看到：

- `chunks/ch_0001.txt`
- `output/chapters/ch_0001.yaml`（skeleton）

### 3) 用 Codex 寫入記憶卡

使用 VS Code / Codex（或其他 LLM），依照：

- `MemoryTemplate.txt`

把每個 chunk 的內容整理成「記憶卡 YAML」。

### 4) 驗證

完成後執行：

```bash
python verify.py
```

若有錯誤，工具會指出：

- 哪個 YAML 檔案
- 哪個欄位缺漏 / 格式錯誤 / schema 不符合


## 🧩 Flexible Schema（重要）

本 repo 的核心設計：**`schema.yaml` = 唯一真實來源（SSOT）**。

### ✅ 修改模板的方式

當你想新增欄位（例如 `emotion_tone` / `chapter_id` / `relations`）：

1. 修改 `schema.yaml`
2. 重新執行 `python split.py` 產生新 skeleton
3. 依新規則填寫 YAML，並執行 `python verify.py`

> 結果：你不需要同步修改 `split.py` / `verify.py` 的欄位定義。


## 🛡️ Validation Policy（避免幻覺）

- ✅ 只允許填寫 skeleton 既有欄位  
- ❌ 不允許新增欄位（避免 schema drift）  
- ❌ 不允許臆測未在 chunk 出現的資訊（避免 hallucination）  
- ✅ 建議「引用 chunk 的關鍵句」作為 evidence

---

## 🔧 Troubleshooting

### Q: verify.py 說欄位缺漏或格式錯誤？
A: 回到對應 YAML 補齊欄位 / 修正格式，再跑一次 `python verify.py`。

### Q: 我想新增欄位，要改哪些檔案？
A: 基本上只改 `schema.yaml`，必要時同步更新 `MemoryTemplate.txt` 的填寫說明。

