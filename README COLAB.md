
# 生成式智能體（森林尋光版）- Google Colab 運行指南

本項目基於斯坦福大學和谷歌于2023年8月開源的[Generative Agents](https://github.com/joonspk-research/generative_agents)項目，通過AI模擬真實的人類生活。

本指南將指導你如何在 Google Colab 上運行「森林尋光」版生成式智能體。
本教程不需要昂貴的 GPU 算力，將使用 Google Gemini API 作為大腦，數據將永久存儲在你的 Google Drive 中。

## 1. 環境配置與代碼獲取：

### 1.1 第一步：挂載 Google Drive：

請在 Colab 中新建一個筆記本（Notebook），然後按順序複製並運行以下代碼塊。

```
from google.colab import drive
import os

print("📂 正在挂載 Google Drive...")
drive.mount('/content/drive')

# 設定工作目錄為 Drive 中的 MyDrive
work_dir = '/content/drive/MyDrive'
os.chdir(work_dir)
print(f"✅ 當前工作目錄：{os.getcwd()}")
```

### 1.2 第二步：拉取項目代碼

如果你的網盤裏還沒有該項目，這段代碼會自動下載。如果已經有了，它會跳過。

```
from google.colab import drive
import os

print("📂 1. 正在掛載 Google Drive...")
drive.mount('/content/drive')

# --- 先定義路徑，並強制切換 ---
work_dir = '/content/drive/MyDrive'
os.chdir(work_dir) 
print(f"📍 2. 已切換工作目錄至: {os.getcwd()}")

# --- 3. 開始下載 ---
repo_url = "https://github.com/Billy200212/GenerativeAgents_Forest-of-Light.git"
project_name = "GenerativeAgents_Forest-of-Light"
project_path = os.path.join(work_dir, project_name)

if not os.path.exists(project_path):
    print("⬇️ 3. 正在下載項目代碼 (Git Clone)...")
    !git clone {repo_url}
else:
    print("✅ 項目已存在，跳過下載。")

# --- 4. 最後進入項目內部 ---
os.chdir(project_path)
print(f"✅ 準備就緒！當前位置: {os.getcwd()}")
```

### 1.3 第三步：安裝依賴庫

安裝項目運行所需的 Python 包。

```
print("🛠️ 正在安裝依賴環境...")
!pip install -r requirements.txt
print("✅ 環境安裝完成！")
```

## 2. 配置 AI 模型 (Gemini API):

前往 `generative_agents/data/config.json` 文件中將 `base_url` 以及 `api_key` 複製其中

## 3. 運行虛擬小鎮

一切準備就緒，現在開始運行模擬。

### 3.1 啓動模擬:

參數説明:
- `name` - 本次模擬的存檔名稱（例如 sim-test-01），需要設定唯一的名稱，用於事後回放。
- `start` - 虛擬小鎮的起始時間。
- `step` - 在迭代多少步之後停止運行。
- `stride` - 每一步迭代在虛擬小鎮中對應的時間（分鐘）。假如設定 `--stride 10`，虛擬小鎮在迭代過程中的時間變化將會是 9:00，9:10，9:20 ...

```
import os

# 確保在正確的子目錄
if os.path.exists('generative_agents'):
    os.chdir('generative_agents')

print("🎬 開始運行模擬 (請耐心等待)...")
# 運行命令
!python start.py --name sim-test-01 --start "20250213-12:00" --step 20 --stride 5
```

## 4. 回放與觀看

模擬結束後，通過網頁觀看小鎮居民的生活回放。

### 4.1 生成數據並啓動網頁

注意： 運行此代碼後，會顯示一個鏈接。點擊該鏈接即可打開回放頁面。

```
import os
from google.colab.output import eval_js

# 👇 必須與上面運行的名稱一致！
sim_name = "sim-test-01"

print(f"📦 正在處理回放數據: {sim_name}...")

# 1. 壓縮數據
ret = os.system(f"python compress.py --name {sim_name}")

if ret == 0:
    # 2. 獲取 Colab 的代理網址 (Port 5000)
    proxy_url = eval_js("google.colab.kernel.proxyPort(5000)")
    full_url = f"{proxy_url}?name={sim_name}"
    
    print("\n" + "="*50)
    print(f"🎉 點擊下方鏈接觀看回放：")
    print(full_url)
    print("="*50 + "\n")

    print("🚀 正在啓動服務器... (請保持此單元格運行，不要關閉)")
    !python replay.py
else:
    print("❌ 數據壓縮失敗，請檢查模擬名稱是否正確。")
```

### 4.2 操作説明

點擊上方生成的 https://...colab.googleusercontent.com/... 鏈接。

操作説明：  
- `鼠標中鍵/方向鍵` - 平移畫面。
- `鼠標滾輪` - 縮放地圖。
- `底部角色欄` - 點擊任意角色可以開啓相機鎖定跟隨。
- `頂部菜單` - 播放回放以及顯示對話

## 5. 常見問題 (FAQ)

1. 下次打開還需要重新下載嗎？
-  不需要。代碼已經存在你的 Google Drive 裏。
-  下次只需要運行 「第一步：挂載 Drive」、「第三步：安裝依賴」 和 「運行模擬」 即可。

2. 報錯 ModuleNotFoundError？
-  這是因爲 Colab 重啓後環境重置了。請重新運行 「第三步：安裝依賴」。

3. 回放網頁打不開？
-  確保最後一個代碼單元格正在轉圈圈（運行中）。
-  嘗試刷新鏈接。