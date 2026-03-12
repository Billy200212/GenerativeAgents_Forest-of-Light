# 1. 選擇基礎環境：我們需要 Python 3.12 版本的乾淨系統
FROM python:3.12-slim

# 2. 設定工作目錄：相當於在便當盒裡建一個叫 /app 的隔間
WORKDIR /app

# 3. 先把 requirements.txt 複製進去
COPY requirements.txt .

# 4. 安裝所有依賴庫 (這步只會在打包時跑一次，以後都不用再裝了！)
RUN pip install --no-cache-dir -r requirements.txt

# 5. 把你專案的所有代碼複製到 /app 裡面
COPY . .

# 6. 因為我們的執行指令都在 generative_agents 裡面，所以預設進入這個目錄
WORKDIR /app/generative_agents

# 7. 對外開放 5000 端口 (這是給回放網頁用的)
EXPOSE 5000

# 8. 預設啟動命令：打開一個終端機讓我們可以輸入指令
CMD ["/bin/bash"]