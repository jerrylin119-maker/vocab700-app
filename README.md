# 700 單字英文學習與測驗 Web App

給 Timmy 與 Chloe（以及其他自訂學員）用的 700 核心單字學習系統，用 [Streamlit](https://streamlit.io/) 打造，部署在 Streamlit Community Cloud：

**👉 <https://timmy-vocab700-app.streamlit.app/>**

## 功能

- **📚 單元學習**：70 個單元、每單元 10 字，支援單字卡（翻面看中文）與列表檢視，含衍生詞、同反義詞、例句、發音（瀏覽器原生 Web Speech API，不需額外服務）。
- **✍️ 隨堂測驗**：同單元打散出題的選擇題測驗。
- **📊 學習儀表板**：70 單元掌握度矩陣、Timmy vs Chloe 對比榜、測驗歷程與錯題診斷，並可匯出/匯入/重設全家進度。
- **📝 我的單字本**：使用者自行輸入不熟悉的單字，系統自動查詢（先查 700 字庫，查不到再查線上字典 API），可閃卡複習或出測驗。
- **📖 單字庫與上傳**：搜尋內建 700 字庫、上傳自訂 CSV/JSON 單字集、下載範本。
- 每位學員（Timmy / Chloe / 自訂新增學員）的進度、測驗分數與個人單字本互相獨立，並會記住每人上次讀到哪個單元第幾個字。

## 架構

```
app.py                      # 主入口，側邊欄導覽 + 5 個功能頁籤
components/
  flashcard.py               # 單字卡 / 列表檢視
  quiz_engine.py              # 隨堂測驗出題與計分
  progress_tracker.py         # 進度持久化 + 學習儀表板（見下方「資料持久化」）
  word_bank.py                 # 個人單字本（新增/查詢/複習/測驗）
  audio_player.py               # 瀏覽器 Web Speech API 發音按鈕
utils/
  data_loader.py               # 讀取 data/default_vocab.json、解析上傳檔案、搜尋
data/
  default_vocab.json           # 內建 700 字資料庫（70 單元）
  vocab_template.csv           # 使用者上傳自訂字庫的範本格式
  user_progress.json           # 本機備援用（.gitignore 排除，正式資料存在 GitHub，見下方）
scripts/                      # 一次性資料集產生腳本，app 執行時不會用到，見 scripts/README.md
styles/custom.css
```

## 資料持久化（重要，接手前請先讀）

Streamlit Community Cloud 的容器是**會重啟/休眠的**，本機檔案系統不保證存活。所以這個 app 沒有用真正的資料庫，而是把 `data/user_progress.json`（所有學員的進度、測驗紀錄、單字本）存在這個 repo 的 **`data-storage` 分支**上，透過 GitHub Contents API 讀寫：

- 讀取：先打 GitHub API 抓 `data-storage` 分支上的 `data/user_progress.json`；抓不到（例如本機開發、沒設定 token）才退回讀本機檔案。
- 寫入：本機一定會先寫一份（同一個容器生命週期內夠用、夠快），接著視情況同步到 GitHub：
  - **重要事件**（測驗交卷、新增/刪除單字本單字、切換學員、新增學員、匯入備份、重設進度）→ **立即**同步到 GitHub，失敗會跳出警告（`st.warning`），不會靜默失敗。
  - **高頻率、低風險事件**（翻卡片、切單元這種單純的閱讀位置更新）→ 節流（目前 20 秒內最多同步一次），避免每點一下就在 `data-storage` 分支多一個 commit。

`GITHUB_TOKEN` 存在 Streamlit Cloud 的 **App settings → Secrets**（`st.secrets["GITHUB_TOKEN"]`），**不會**出現在 repo 裡。維護備忘：

- 這個 token 只需要對本 repo 的 **Contents 讀寫**權限，建議用 fine-grained PAT 並限定 repo。
- 如果是有到期日的 token，記得排提醒去 Streamlit Cloud 換新的，不然存檔會開始「本機存了但雲端沒同步」（會跳警告，但不會再自動重試，要等下一次寫入事件才會再試）。
- `data-storage` 分支的 commit 數量會持續增加（每次重要事件一個 commit），這是設計上的取捨，不是 bug；如果哪天想換成真正的資料庫（例如 Supabase / SQLite + 定期備份），`progress_tracker.py` 是唯一要動的地方。

## 本機開發

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

沒有設定 `GITHUB_TOKEN` 也能跑，只是進度只會存在本機 `data/user_progress.json`，重啟就消失——這是預期行為，不是壞掉。

## 部署

Streamlit Community Cloud 從 `main` 分支自動部署，push 到 `main` 就會自動重新部署。`data-storage` 分支**只**用來存資料，不會被部署，也不應該把它跟 `main` merge。
