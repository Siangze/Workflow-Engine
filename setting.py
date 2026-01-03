import json
import os
import shutil
import sys

class SettingsManager:
    def __init__(self):
        self.global_config_path = os.path.join("configs", "global_config.json")
        self.flow_config_path = os.path.join("configs", "config.json")
        self.tasks_dir = "tasks"

        # 確保 tasks 資料夾存在
        if not os.path.exists(self.tasks_dir):
            os.makedirs(self.tasks_dir)

    def load_global_config(self):
        """讀取全域設定"""
        try:
            if not os.path.exists(self.global_config_path):
                return {}
            with open(self.global_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading global config: {e}")
            return {}

    def save_global_config(self, data):
        """儲存全域設定"""
        try:
            with open(self.global_config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving global config: {e}")
            return False

    def load_flow_config(self):
        """讀取流程設定"""
        try:
            if not os.path.exists(self.flow_config_path):
                return {}
            with open(self.flow_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading flow config: {e}")
            return {}

    def save_flow_config(self, data):
        """儲存流程設定"""
        try:
            with open(self.flow_config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving flow config: {e}")
            return False

    def import_script(self, source_path):
        """匯入 Python 腳本到 tasks 資料夾"""
        try:
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"Source file not found: {source_path}")

            filename = os.path.basename(source_path)
            if not filename.endswith('.py'):
                raise ValueError("Only .py files are supported")

            target_path = os.path.join(self.tasks_dir, filename)
            
            # 如果來源就是目標，則不用複製
            if os.path.abspath(source_path) != os.path.abspath(target_path):
                shutil.copy2(source_path, target_path)

            # 回傳 module 名稱 (不含副檔名)
            return os.path.splitext(filename)[0]
        except Exception as e:
            print(f"Error importing script: {e}")
            raise e

    def get_module_name_from_path(self, path):
         filename = os.path.basename(path)
         return os.path.splitext(filename)[0]
