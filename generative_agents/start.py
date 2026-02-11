import os
import copy
import json
import argparse
import datetime
import math

from dotenv import load_dotenv, find_dotenv

from modules.game import create_game, get_game
from modules import utils

# 定義模擬中出現的角色列表
personas = [
    "Brian", "小兔子", "小松鼠", "小烏龜", "小熊", "小羊", "小貓",
]


class SimulateServer:
    def __init__(self, name, static_root, checkpoints_folder, config, start_step=0, verbose="info", log_file=""):
        self.name = name
        self.static_root = static_root
        self.checkpoints_folder = checkpoints_folder
        self.config = config

        # 創建存檔文件夾
        os.makedirs(checkpoints_folder, exist_ok=True)

        # 加載對話日誌，如果存在則讀取，否則初始化為空
        self.conversation_log = f"{checkpoints_folder}/conversation.json"
        if os.path.exists(self.conversation_log):
            with open(self.conversation_log, "r", encoding="utf-8") as f:
                conversation = json.load(f)
        else:
            conversation = {}

        # 設置日誌記錄器
        if len(log_file) > 0:
            self.logger = utils.create_file_logger(f"{checkpoints_folder}/{log_file}", verbose)
        else:
            self.logger = utils.create_io_logger(verbose)

        # 初始化游戲核心邏輯
        game = create_game(name, static_root, config, conversation, logger=self.logger)
        game.reset_game()

        self.game = get_game()
        self.tile_size = self.game.maze.tile_size
        self.agent_status = {}

        # 加載 Agent 的基礎配置        
        if "agent_base" in config:
            agent_base = config["agent_base"]
        else:
            agent_base = {}

        # 初始化每個 Agent 的狀態，包括坐標和路徑        
        for agent_name, agent in config["agents"].items():
            agent_config = copy.deepcopy(agent_base)
            agent_config.update(self.load_static(agent["config_path"]))
            self.agent_status[agent_name] = {
                "coord": agent_config["coord"],# 當前物理坐標
                "path": [],                    # 未來計劃要走的路徑隊列
            }

        # 計算思考間隔
        self.think_interval = max(
            a.think_config["interval"] for a in self.game.agents.values()
        )
        self.start_step = start_step

    def simulate(self, step, stride=0):
        """
        核心模擬循環
        :param step: 本次運行的總步數
        :param stride: 每一步模擬的時間跨度（分鐘），例如 5 分鐘
        """
        timer = utils.get_timer()
        
        # [物理限制參數]
        # SPEED = 2 表示角色每分鐘只能移動 2 個網格。
        # 這是修復瞬移 Bug 的基礎：限制了角色的最大移動能力。
        SPEED = 2 

        for i in range(self.start_step, self.start_step + step):
            if stride > 0:
                timer.forward(stride) # 推進時間
            
            sim_time = timer.get_date("%Y%m%d-%H:%M")
            title = "Simulate Step[{}/{}, time: {}]".format(i+1, self.start_step + step, sim_time)
            self.logger.info("\n" + utils.split_line(title, "="))

            # [計算最大移動步數]
            # 這是修復的核心邏輯之一。
            # 根據時間跨度 (stride, 如5分鐘) 和速度 (SPEED, 2格/分)，計算本回合物理上最多能走幾格。
            # 例如：5分鐘 * 2格 = 10格。即使目的地在 100 格以外，本回合也只能走 10 格。
            max_moves = max(1, int(stride * SPEED))

            # 1. 決策階段 (Cognition)
            # LLM 決定去哪裡，或者是否停下來說話。
            # 如果 Agent 決定移動，agent_think 會返回一條完整的 A* 尋路路徑。
            for name, status in self.agent_status.items():
                plan = self.game.agent_think(name, status)["plan"]
                agent = self.game.get_agent(name)
                
                if name not in self.config["agents"]:
                    self.config["agents"][name] = {}
                self.config["agents"][name].update(agent.to_dict())

                # 如果決策產生了移動路徑，將其存入 status["path"]
                # 這裡的 path 可能非常長（例如從家走到森林深處），遠超本回合能走的距離。
                if plan.get("path"):
                    status["path"] = plan["path"]

            # 2. 移動階段 (Movement Physics) - [修復瞬移 Bug 的關鍵代碼]
            # 舊版本問題：直接將 status["coord"] 設置為 path 的最後一個點，導致角色瞬間到達目的地。
            # 舊版本後果：角色物理上瞬間到達B點，但邏輯上可能還沒發生交互，導致回放時空間錯亂。
            #
            # 新版本邏輯（分步移動）：
            # 我們不關心路徑有多長，只關心本回合(max_moves)能走多遠。
            # 循環執行 max_moves 次，每次只走一格。
            for move_idx in range(max_moves):
                anyone_moved = False
                for name, status in self.agent_status.items():
                    # 檢查是否還有路徑要走
                    if status["path"] and len(status["path"]) > 0:
                        # [關鍵操作] pop(0) 取出路徑列表的第一個坐標（即下一步）。
                        # 將角色的物理坐標更新為這一步的位置。
                        status["coord"] = status["path"].pop(0)
                        anyone_moved = True
                
                # 如果所有人都走完了計劃路徑（或者本來就不需要走），提前結束循環，節省資源。
                if not anyone_moved:
                    break

            # 此時，status["coord"] 停留在角色本回合能到達的最遠位置。
            # 如果路徑很長，status["path"] 裡還有剩餘坐標，留給下一個 simulation step 繼續走。

            # 3. 數據保存
            for name, status in self.agent_status.items():
                # 將計算後的真實物理坐標寫入配置，用於生成前端展示數據
                self.config["agents"][name].update(
                    {"coord": status["coord"]}
                )
                
                # [視覺修復]
                # 這是為了配合分步移動邏輯的顯示優化。
                # 如果 status["path"] 還有剩餘（説明還沒走到目的地，是被 max_moves 截斷了），
                # 我們需要強制將前端顯示的 Action 描述改為“移動中”。
                # 這樣在回放時，用戶會看到角色正在走，而不是顯示抵達目的地後的任務。
                if status["path"] and len(status["path"]) > 0:
                    if "action" not in self.config["agents"][name]:
                        self.config["agents"][name]["action"] = {"event": {}}
                    if "event" not in self.config["agents"][name]["action"]:
                        self.config["agents"][name]["action"]["event"] = {}

                    curr_desc = self.config["agents"][name]["action"]["event"].get("describe", "")
                    if "前往" not in curr_desc:
                        self.config["agents"][name]["action"]["event"]["object"] = "移動中"
                        self.config["agents"][name]["action"]["event"]["emoji"] = "🚶"
                        self.config["agents"][name]["action"]["event"]["describe"] = f"正在前往目的地 (剩餘{len(status['path'])}步)"

            self.config.update({
                "time": sim_time,
                "step": i + 1,
            })
            
            # 保存當前步的快照
            with open(f"{self.checkpoints_folder}/simulate-{sim_time.replace(':', '')}.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(self.config, indent=2, ensure_ascii=False))
            with open(f"{self.checkpoints_folder}/conversation.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(self.game.conversation, indent=2, ensure_ascii=False))

    def load_static(self, path):
        return utils.load_dict(os.path.join(self.static_root, path))


def get_config_from_log(checkpoints_folder):
    files = sorted(os.listdir(checkpoints_folder))
    json_files = list()
    for file_name in files:
        if file_name.endswith(".json") and file_name != "conversation.json":
            json_files.append(os.path.join(checkpoints_folder, file_name))
    if len(json_files) < 1: return None
    with open(json_files[-1], "r", encoding="utf-8") as f: config = json.load(f)
    assets_root = os.path.join("assets", "village")
    start_time = datetime.datetime.strptime(config["time"], "%Y%m%d-%H:%M")
    start_time += datetime.timedelta(minutes=config["stride"])
    config["time"] = {"start": start_time.strftime("%Y%m%d-%H:%M")}
    agents = config["agents"]
    for a in agents: config["agents"][a]["config_path"] = os.path.join(assets_root, "agents", a.replace(" ", "_"), "agent.json")
    return config

def get_config(start_time="20240213-09:30", stride=15, agents=None):
    with open("data/config.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
        agent_config = json_data["agent"]
    assets_root = os.path.join("assets", "village")
    config = {
        "stride": stride,
        "time": {"start": start_time},
        "maze": {"path": os.path.join(assets_root, "maze.json")},
        "agent_base": agent_config,
        "agents": {},
    }
    for a in agents:
        config["agents"][a] = {
            "config_path": os.path.join(
                assets_root, "agents", a.replace(" ", "_"), "agent.json"
            ),
        }
    return config

load_dotenv(find_dotenv())
parser = argparse.ArgumentParser(description="console for village")
parser.add_argument("--name", type=str, default="", help="The simulation name")
parser.add_argument("--start", type=str, default="20240213-09:30", help="The starting time of the simulated ville")
parser.add_argument("--resume", action="store_true", help="Resume running the simulation")
parser.add_argument("--step", type=int, default=10, help="The simulate step")
parser.add_argument("--stride", type=int, default=10, help="The step stride in minute")
parser.add_argument("--verbose", type=str, default="debug", help="The verbose level")
parser.add_argument("--log", type=str, default="", help="Name of the log file")
args = parser.parse_args()

if __name__ == "__main__":
    checkpoints_path = "results/checkpoints"
    name = args.name
    if len(name) < 1: name = input("Please enter a simulation name (e.g. sim-test): ")
    resume = args.resume
    if resume:
        while not os.path.exists(f"{checkpoints_path}/{name}"): name = input(f"'{name}' doesn't exists, please re-enter the simulation name: ")
    else:
        while os.path.exists(f"{checkpoints_path}/{name}"): name = input(f"The name '{name}' already exists, please enter a new name: ")
    checkpoints_folder = f"{checkpoints_path}/{name}"
    start_time = args.start
    if resume:
        sim_config = get_config_from_log(checkpoints_folder)
        if sim_config is None:
            print("No checkpoint file found to resume running.")
            exit(0)
        start_step = sim_config["step"]
    else:
        sim_config = get_config(start_time, args.stride, personas)
        start_step = 0
    static_root = "frontend/static"
    server = SimulateServer(name, static_root, checkpoints_folder, sim_config, start_step, args.verbose, args.log)
    server.simulate(args.step, args.stride)