import os
import json
import argparse
import math
from datetime import datetime

# 引入 Maze 模塊用於查詢地圖信息
from modules.maze import Maze
from start import personas

file_markdown = "simulation.md"
file_movement = "movement.json"

# [設置] 60幀 = 1秒
frames_per_step = 60  

def get_stride(json_files):
    if len(json_files) < 1:
        return 1
    with open(json_files[-1], "r", encoding="utf-8") as f:
        config = json.load(f)
    return config["stride"]

def get_location_str(address_list):
    """
    將地址列表轉換為字符串，例如 ['the Ville', '家', '床'] -> '家，床'
    """
    if isinstance(address_list, str):
        return address_list
    if len(address_list) > 1:
        return "，".join(address_list[1:])
    return address_list[0]

def insert_frame0(init_pos, movement, agent_name):
    """
    插入第0幀（初始狀態），確保回放一開始角色就在正確的位置
    """
    key = "0"
    if key not in movement.keys():
        movement[key] = dict()

    json_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
    # 確保路徑存在，防止報錯
    if not os.path.exists(json_path):
        # 嘗試備用路徑（兼容不同項目結構）
        json_path = f"assets/village/agents/{agent_name}/agent.json"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            # 初始狀態通常讀取 living_area
            address = json_data["spatial"]["address"]["living_area"]
            coord = json_data["coord"]
            currently = json_data["currently"]
            scratch = json_data["scratch"]
    except:
        # 如果讀取出錯，給默認值
        address = ["World", "Unknown"]
        coord = [0, 0]
        currently = "未知狀態"
        scratch = {}

    location = get_location_str(address)
    init_pos[agent_name] = coord
    
    movement[key][agent_name] = {
        "location": location,
        "movement": coord,
        "description": "初始狀態", 
    }
    movement["description"][agent_name] = {
        "currently": currently,
        "scratch": scratch,
    }

def generate_movement(checkpoints_folder, compressed_folder, compressed_file):
    """
    核心函數：將後端生成的離散存檔數據，壓縮並平滑化為前端可播放的連續幀數據。
    
    【修復說明 - 流暢移動】：
    後端模擬可能是跳躍的（例如：Step 1 在 A點，Step 2 在 B點）。
    如果角色在 Step 1 內只花了很少時間就走到了 B 點，剩下的時間它會停在原地等待 Step 2。
    這會導致回放時出現「快走 -> 傻站著 -> 快走」的鬼畜效果。
    
    本函數通過計算 A 點到 B 點的路徑，並將其均勻插值分配到 frames_per_step (例如60幀) 中。
    這樣前端看到的就是角色在整個 Step 時間內勻速、流暢地從 A 移動到 B，消除了中間的停頓。
    """
    movement_file = os.path.join(compressed_folder, compressed_file)

    conversation_file = "conversation.json"
    conversation = {}
    if os.path.exists(os.path.join(checkpoints_folder, conversation_file)):
        with open(os.path.join(checkpoints_folder, conversation_file), "r", encoding="utf-8") as f:
            conversation = json.load(f)

    files = sorted(os.listdir(checkpoints_folder))
    json_files = list()
    for file_name in files:
        if file_name.endswith(".json") and file_name != conversation_file:
            json_files.append(os.path.join(checkpoints_folder, file_name))

    persona_init_pos = dict()
    all_movement = dict()
    all_movement["description"] = dict()
    all_movement["conversation"] = dict()

    stride = get_stride(json_files)
    sec_per_step = stride 

    result = {
        "start_datetime": "",
        "stride": stride,
        "sec_per_step": sec_per_step,
        "persona_init_pos": persona_init_pos,
        "all_movement": all_movement,
    }

    last_location = dict()

    # 【修復說明 - 實時位置顯示】：
    # 為了顯示角色“腳下踩著的地方”，而不是“腦子裡想去的地方”，因此需要加載地圖數據。
    # 這裏加載 maze.json，用於稍後通過坐標反查地塊名稱。
    maze_json_path = "frontend/static/assets/village/maze.json"
    if not os.path.exists(maze_json_path):
        maze_json_path = "assets/village/maze.json"
    
    maze_object = None
    if os.path.exists(maze_json_path):
        with open(maze_json_path, "r", encoding="utf-8") as f:
            maze_data = json.load(f)
            maze_object = Maze(maze_data, None)

    # 遍歷每一個存檔文件（每一個模擬步驟）
    for file_name in json_files:
        with open(file_name, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            step = json_data["step"]
            agents = json_data["agents"]

            if len(result["start_datetime"]) < 1:
                t = datetime.strptime(json_data["time"], "%Y%m%d-%H:%M")
                result["start_datetime"] = t.isoformat()

            for agent_name, agent_data in agents.items():
                if step == 1:
                    insert_frame0(persona_init_pos, all_movement, agent_name)

                # 獲取上一幀的位置作為起點
                source_coord = last_location.get(agent_name, all_movement["0"][agent_name])["movement"]
                src_grid = (int(round(source_coord[0])), int(round(source_coord[1])))

                # 獲取本回合的目標位置（這是後端計算出的本 Step 結束時的位置）
                target_coord = agent_data["coord"]
                
                # 獲取“目的地”名稱 (這是 Cognitive 目的地，比如“去臥室”)
                # 注意：這只是意圖，不代表現在就在那裡
                destination_name = get_location_str(agent_data["action"]["event"]["address"])

                # 路徑規劃：計算從起點到終點的實際行走軌跡                
                if destination_name is None:
                    # 如果沒有目的地，可能是在原地
                    destination_name = last_location.get(agent_name, all_movement["0"][agent_name])["location"]
                    full_path = [src_grid]
                else:
                    # 使用 Maze 進行 A* 尋路，找出物理路徑
                    if maze_object:
                        full_path = maze_object.find_path(src_grid, target_coord)
                    else:
                        full_path = [src_grid, target_coord]

                # 處理對話記錄
                had_conversation = False
                step_conversation = ""
                persons_in_conversation = []
                step_time = json_data["time"]
                if step_time in conversation.keys():
                    for chats in conversation[step_time]:
                        for persons, chat in chats.items():
                            persons_in_conversation.append(persons.split(" @ ")[0].split(" -> "))
                            step_conversation += f"\n地点：{persons.split(' @ ')[1]}\n\n"
                            for c in chat:
                                agent = c[0]
                                text = c[1]
                                step_conversation += f"{agent}：{text}\n"

                # [關鍵修復 - 亞像素平滑插值]
                # 將離散的網格路徑 (full_path) 轉換為連續的平滑動畫幀 (smooth_path)。
                # 無論路徑長短，我們都將其拉伸/壓縮到 frames_per_step (例如60幀) 的長度。
                # 這樣做的好處是：前端播放時，角色總是在勻速移動，不會出現“走兩步停三步”的情況。
                smooth_path = []
                path_len = len(full_path)
                
                if path_len <= 1:
                    smooth_path = [list(target_coord)] * frames_per_step
                else:
                    total_segments = path_len - 1
                    for i in range(frames_per_step):
                        # 計算當前幀在整個路徑中的百分比進度 (0.0 ~ 1.0)
                        progress = i / (frames_per_step - 1) if frames_per_step > 1 else 1.0
                        exact_pos = progress * total_segments
                        segment_idx = int(exact_pos)
                        if segment_idx >= total_segments:
                            segment_idx = total_segments - 1

                        # 局部插值：計算在兩個網格點之間的精確位置
                        local_progress = exact_pos - segment_idx
                        p1 = full_path[segment_idx]
                        p2 = full_path[segment_idx + 1]
                        interp_x = p1[0] + (p2[0] - p1[0]) * local_progress
                        interp_y = p1[1] + (p2[1] - p1[1]) * local_progress
                        smooth_path.append([interp_x, interp_y])

                # 寫入每一幀的數據
                for i in range(frames_per_step):
                    movement = smooth_path[i]
                    moving = (i < frames_per_step - 1) and (path_len > 1)

                    if agent_name not in last_location.keys():
                        last_location[agent_name] = dict()
                    
                    # 更新緩存，供下一輪使用
                    last_location[agent_name]["movement"] = target_coord
                    last_location[agent_name]["location"] = destination_name

                    # [關鍵修復 - 計算實時位置]
                    # 這裡不再直接使用 destination_name（那只是意圖）。
                    # 而是拿當前幀的精確坐標 (movement)，去詢問 Maze 對象：
                    # "我現在在坐標 (x, y)，請問這裡是地圖上的哪裡？"
                    real_current_location = destination_name
                    if maze_object and movement:
                        try:
                            # 獲取當前這一微小時刻的整數坐標
                            cur_x, cur_y = int(round(movement[0])), int(round(movement[1]))
                            # 查詢該坐標對應的地塊信息
                            curr_tile = maze_object.tile_at((cur_x, cur_y))
                            if curr_tile:
                                # 獲取地址列表，例如 ['the Ville', '道路', '主幹道']
                                addr_list = curr_tile.get_address(as_list=True)
                                # 轉換為字符串，如 "道路，主幹道"
                                real_current_location = get_location_str(addr_list)
                        except Exception:
                            # 如果出錯（例如坐標越界），就保持默認值
                            pass

                    # 構造 Action 描述 (意圖)
                    if moving:
                        # 這裡顯示意圖：正在前往 [目的地]
                        action = f"前往 {destination_name}"
                    else:
                        # 停止時，顯示具體行爲 (例如 "正在睡覺")
                        action = agent_data["action"]["event"]["describe"]
                        if len(action) < 1:
                            action = f'{agent_data["action"]["event"]["predicate"]}{agent_data["action"]["event"]["object"]}'

                        for persons in persons_in_conversation:
                            if agent_name in persons:
                                had_conversation = True
                                break

                        if "睡觉" in action:
                            action = "😴 " + action
                        elif had_conversation:
                            action = "💬 " + action

                    step_key = "%d" % ((step-1) * frames_per_step + 1 + i)
                    if step_key not in all_movement.keys():
                        all_movement[step_key] = dict()

                    if movement is not None:
                        all_movement[step_key][agent_name] = {
                            "location": real_current_location, # 修復點：前端 @ 後面現在顯示的是真實物理位置
                            "movement": movement,              # 平滑插值後的坐標 
                            "action": action,                  # 前端顯示的活動意圖
                        }
                all_movement["conversation"][step_time] = step_conversation

    with open(movement_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=2, ensure_ascii=False))

    return result


# ==========================================
#  Markdown 報告生成 (已修復位置顯示問題)
# ==========================================
def generate_report(checkpoints_folder, compressed_folder, compressed_file):
    last_state = dict()

    conversation_file = "conversation.json"
    conversation = {}
    if os.path.exists(os.path.join(checkpoints_folder, conversation_file)):
        with open(os.path.join(checkpoints_folder, conversation_file), "r", encoding="utf-8") as f:
            conversation = json.load(f)

    # [新增] 加載地圖用於 Markdown 報告的真實位置查詢
    # 這樣在生成的報告中，角色位置也是準確的物理位置，而非意圖位置
    maze_json_path = "frontend/static/assets/village/maze.json"
    if not os.path.exists(maze_json_path):
        maze_json_path = "assets/village/maze.json"
    
    maze_object = None
    if os.path.exists(maze_json_path):
        with open(maze_json_path, "r", encoding="utf-8") as f:
            maze_data = json.load(f)
            maze_object = Maze(maze_data, None)

    def extract_description():
        markdown_content = "# 基础人设\n\n"
        for agent_name in personas:
            json_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
            if not os.path.exists(json_path):
                 json_path = f"assets/village/agents/{agent_name}/agent.json"
            
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                    markdown_content += f"## {agent_name}\n\n"
                    markdown_content += f"年龄：{json_data['scratch']['age']}岁  \n"
                    markdown_content += f"先天：{json_data['scratch']['innate']}  \n"
                    markdown_content += f"后天：{json_data['scratch']['learned']}  \n"
                    markdown_content += f"生活习惯：{json_data['scratch']['lifestyle']}  \n"
                    markdown_content += f"当前状态：{json_data['currently']}\n\n"
        return markdown_content

    def extract_action(json_data):
        markdown_content = ""
        agents = json_data["agents"]
        for agent_name, agent_data in agents.items():
            if agent_name not in last_state.keys():
                last_state[agent_name] = {"currently": "", "location": "", "action": ""}

            # --- [關鍵修復 - 報告中的位置準確性] ---
            # 獲取角色當前的物理坐標
            real_coord = agent_data["coord"]
            
            # 默認使用 Cognitive Location (如果地圖查詢失敗)
            real_location_str = get_location_str(agent_data["action"]["event"]["address"])
            
            # 嘗試使用物理坐標反查 Maze 對象獲取真實位置
            if maze_object:
                try:
                    cur_x, cur_y = int(round(real_coord[0])), int(round(real_coord[1]))
                    curr_tile = maze_object.tile_at((cur_x, cur_y))
                    if curr_tile:
                        addr_list = curr_tile.get_address(as_list=True)
                        real_location_str = get_location_str(addr_list)
                except:
                    pass
            
            # Action 依然顯示描述 (例如：正在前往目的地...)
            action = agent_data["action"]["event"]["describe"]
            
            # 去重：如果位置和動作都沒變，就不重複寫入日誌
            if real_location_str == last_state[agent_name]["location"] and action == last_state[agent_name]["action"]:
                continue

            last_state[agent_name]["location"] = real_location_str
            last_state[agent_name]["action"] = action

            if len(markdown_content) < 1:
                markdown_content = f"# {json_data['time']}\n\n"
                markdown_content += "## 活动记录：\n\n"

            markdown_content += f"### {agent_name}\n"

            if len(action) < 1:
                action = "睡觉"

            # 寫入 Markdown：這裡是真實位置
            markdown_content += f"位置：{real_location_str}  \n"
            markdown_content += f"活动：{action}  \n"

            markdown_content += f"\n"

        if json_data['time'] not in conversation.keys():
            return markdown_content

        markdown_content += "## 对话记录：\n\n"
        for chats in conversation[json_data['time']]:
            for agents, chat in chats.items():
                markdown_content += f"### {agents}\n\n"
                for item in chat:
                    markdown_content += f"`{item[0]}`\n> {item[1]}\n\n"
        return markdown_content

    all_markdown_content = extract_description()
    files = sorted(os.listdir(checkpoints_folder))
    for file_name in files:
        if (not file_name.endswith(".json")) or (file_name == conversation_file):
            continue

        file_path = os.path.join(checkpoints_folder, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            content = extract_action(json_data)
            all_markdown_content += content + "\n\n"
    with open(f"{compressed_folder}/{compressed_file}", "w", encoding="utf-8") as compressed_file:
        compressed_file.write(all_markdown_content)


parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str, default="", help="the name of the simulation")
args = parser.parse_args()


if __name__ == "__main__":
    name = args.name
    if len(name) < 1:
        name = input("Please enter a simulation name: ")

    while not os.path.exists(f"results/checkpoints/{name}"):
        name = input(f"'{name}' doesn't exists, please re-enter the simulation name: ")

    checkpoints_folder = f"results/checkpoints/{name}"
    compressed_folder = f"results/compressed/{name}"
    os.makedirs(compressed_folder, exist_ok=True)

    print(f"Generating Markdown report for {name} (calculating real-time locations)...")
    generate_report(checkpoints_folder, compressed_folder, file_markdown)
    print("Report generated.")
    
    print(f"Compressing movement data for Web Replay...")
    generate_movement(checkpoints_folder, compressed_folder, file_movement)
    print("Compression complete.")