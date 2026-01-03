import json
import os
import sys

class WorkflowModel:
    def __init__(self):
        self.config = self.load_config_from_file()
        self.global_config = self.load_global_config()
        self.python_path = self.global_config.get("python_path", "python") # 預設使用系統 python
        self.current_flow_steps = []
        self.selected_start_idx = 0
        self.is_running = False
        self.stop_requested = False
        self.disabled_lines = set()

    def load_config_from_file(self):
        if getattr(sys, 'frozen', False):
            # 打包後：讀取執行檔同級目錄的configs目錄
            base_path = os.path.join(os.path.dirname(sys.executable), 'configs')
        else:
            # 開發時：讀取腳本所在目錄的configs目錄
            base_path = os.path.join(os.path.dirname(__file__),'configs')
        
        filename = os.path.join(base_path, "config.json")
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def load_global_config(self):
        # 使用與 load_config_from_file 相同的邏輯
        if getattr(sys, 'frozen', False):
            base_path = os.path.join(os.path.dirname(sys.executable), 'configs')
        else:
            base_path = os.path.join(os.path.dirname(__file__), 'configs')
            
        filename = os.path.join(base_path, "global_config.json")
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def set_flow(self, flow_key):
        if flow_key in self.config:
            self.current_flow_steps = self.config[flow_key]["steps"]
            return self.config[flow_key]
        return None