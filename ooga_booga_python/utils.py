import json
import os

def save_swap_history(data, wallet_address: str):
    os.makedirs("swap_history", exist_ok=True)
    file_path = os.path.join("swap_history", f"{wallet_address}.json")
    
    # 读取现有记录
    records = []
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                records = json.load(f)
            except json.JSONDecodeError:
                records = []
    
    # 添加新记录
    records.append(data)
    
    # 保存更新后的记录
    with open(file_path, "w") as f:
        json.dump(records, f, indent=2)