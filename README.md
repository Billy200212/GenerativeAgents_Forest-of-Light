简体中文 | [English](./README_en.md)

# 生成式智能體（Generative Agents）森林尋光版

本項目基於斯坦福大學和谷歌于2023年8月開源的[Generative Agents](https://github.com/joonspk-research/generative_agents)項目，通過AI模擬真實的人類生活。

[GenerativeAgentsCN](https://github.com/x-glacier/GenerativeAgentsCN.git)作爲的生成式智能體的漢化版本，本項目更新了地圖與角色並優化了回放界面，開發了森林尋光的新版本，並配備故事大綱，以測試AI在游戲敘事中的Alignment的程度。

## 1. 準備工作

### 1.1 獲取代碼：

```
git clone https://github.com/x-glacier/GenerativeAgentsCN.git
cd GenerativeAgentsCN
```

### 1.2 配置大語言模型（LLM）

修改配置文件 `generative_agents/data/config.json`:
1. 默認使用[Ollama](https://ollama.com/)加載本地量化模型，并提供OpenAI兼容API。需要先拉取量化模型（參考[ollama.md](docs/ollama.md)），并確保`base_url`和`model`與Ollama中的配置一致。
2. 如果希望調用其他OpenAI兼容API，需要將`provider`改爲`openai`，并根據API文檔修改`model`、`api_key`和`base_url`。

### 1.3 安裝python依賴

建議先使用anaconda3創建並激活虛擬環境：

```
conda create -n generative_agents_cn python=3.12
conda activate generative_agents_cn
```

安装依賴：

```
pip install -r requirements.txt
```

## 2. 運行虛擬小鎮

```
cd generative_agents
python start.py --name sim-test --start "20250213-09:30" --step 10 --stride 10
```

參數説明:
- `name` - 每次啟動虛擬小鎮，需要設定唯一的名稱，用於事後回放。
- `start` - 虛擬小鎮的起始時間。
- `resume` - 在運行結束或意外中斷後，從上次的「斷點」處，繼續運行虛擬小鎮。
- `step` - 在迭代多少步之後停止運行。
- `stride` - 每一步迭代在虛擬小鎮中對應的時間（分鐘）。假如設定 `--stride 10`，虛擬小鎮在迭代過程中的時間變化將會是 9:00，9:10，9:20 ...

## 3. 回放

### 3.1 生成回放數據

```
python compress.py --name <simulation-name>
```

運行結束後將在`results/compressed/<simulation-name>`目錄下生成回放數據文件`movement.json`。同時還將生成`simulation.md`，以時間綫方式呈現每個智能體的狀態及對話内容。

### 3.2 啓動回放服務

```
python replay.py
```

通過瀏覽器打開回放頁面（地址：`http://127.0.0.1:5000/?name=<simulation-name>`），可以看到虛擬小鎮中的居民在各個時間段的活動。

操作説明：  
- `鼠標中鍵/方向鍵` - 平移畫面。
- `鼠標滾輪` - 縮放地圖。
- `Enter` - 播放/暫停。
- `底部角色欄` - 點擊任意角色可以開啓相機鎖定跟隨。

## 4. 修改地圖
`jiejieje`已為本項目開發了一款地圖標注工具，項目地址：https://github.com/jiejieje/tiled_to_maze.json

## 5. 參考資料

### 5.1 論文

[Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)

### 5.2 代碼

[Generative Agents](https://github.com/joonspk-research/generative_agents)

[wounderland](https://github.com/Archermmt/wounderland)

[GenerativeAgentsCN](https://github.com/x-glacier/GenerativeAgentsCN.git)
