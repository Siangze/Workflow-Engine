import threading
import importlib
import time
import sys
import os
from tkinter import messagebox
import subprocess
from view_setting import SettingsView
from view_help import HelpView

class WorkflowPresenter:
    def __init__(self, root):
        self.root = root
        self.model = None 
        self.view = None
        self.is_animating = False
        self.active_line_idx = -1
        self.current_process = None # 儲存當前子進程引用
        self.current_step_index = -1 # 追蹤目前執行的步驟索引

    def init_app(self, model, view):
        self.model = model
        self.view = view
        self.view.combo['values'] = list(self.model.config.keys())
        self.view.start_welcome_animation()

    def handle_flow_change(self, flow_key):
        self.view.stop_welcome_animation()
        if self.model.is_running:
            self.model.stop_requested = True
        self.is_animating = False
        data = self.model.set_flow(flow_key)
        if data:
            self.view.msg_desc.config(text=data["description"])
            self.model.selected_start_idx = 0
            self.view.root.after(50, lambda: self.view.draw_workflow(self.model.current_flow_steps, 0))

    def handle_node_click(self, idx):
        if not self.model.is_running:
            self.model.selected_start_idx = idx
            self.view.update_node_colors(-1, -1, idx)

    def handle_hover(self, event, idx, entering):
        if self.model.is_running: return
        if entering:
            step = self.model.current_flow_steps[idx]
            text = f"【 {step['name']} 】\nfunc: {step.get('overview', 'no description')}"
            self.view.show_tooltip(event, text)
        else:
            self.view.show_tooltip(event, None)

    def handle_run_click(self):
        if not self.model.current_flow_steps: return
        self.view.btn_run.config(state="disabled")
        self.view.toggle_combobox_state(False)
        threading.Thread(target=self.execute_workflow, daemon=True).start()

    def trigger_animation(self):
        self.view.animate_lines_step(self.active_line_idx, self.is_animating)
    
    def log_to_view(self, message):
        """確保跨執行緒安全地更新 UI"""
        self.view.root.after(0, lambda: self.view.write_log(message))

    def handle_line_cancel(self, line_idx):
        """處理取消線段"""
        if self.model.is_running: return
        self.model.disabled_lines.add(line_idx)
        # 立即重繪
        self.view.draw_workflow(self.model.current_flow_steps, self.model.selected_start_idx)
        self.view._perform_hide_icon() # 隱藏圖示

    def handle_help_click(self):
        """開啟說明書"""
        global_config = self.model.load_global_config()
        manual_text = global_config.get("manual", "")
        HelpView(self.view.root, manual_text, self.view.colors)


    def handle_setting_click(self):
        """開啟設定視窗並在關閉後刷新狀態"""
        sv = SettingsView(self.view.root, self.view.colors)
        self.view.root.wait_window(sv)
        
        # 重新讀取設定
        self.model.config = self.model.load_config_from_file()
        self.model.global_config = self.model.load_global_config()
        self.model.python_path = self.model.global_config.get("python_path", "python")
        
        # 更新下拉選單
        current_flows = list(self.model.config.keys())
        self.view.combo['values'] = current_flows
        
        # 檢查當前選擇的流程是否還存在
        current_selection = self.view.combo.get()
        if current_selection and current_selection in current_flows:
            # 重新載入該流程 (因為步驟可能變了)
            self.handle_flow_change(current_selection)
        else:
            # 若流程被刪除與重置
            self.view.combo.set('')
            self.view.msg_desc.config(text="Please select a flow...")
            self.model.current_flow_steps = []
            self.view.draw_workflow([], 0)

    def handle_stop_click(self):
        """處理中止按鈕"""
        if not self.model.is_running: return
        
        self.model.stop_requested = True
        
        current_idx = self.current_step_index
        next_idx = current_idx + 1
        
        # 顯示 Log 提示
        timestamp = time.strftime('%H:%M:%S')
        self.log_to_view(f"[{timestamp}] Step {current_idx + 1} is running, user stop, will take effect from the next step, stop execution step {next_idx + 1} and later process\n")

    def handle_reset_click(self):
        if self.model.is_running: return
        self.model.selected_start_idx = 0
        self.model.disabled_lines = set() # 重置禁用線段
        self.view.reset_view_state()
        if self.model.current_flow_steps:
            self.view.draw_workflow(self.model.current_flow_steps, 0)

    def execute_workflow(self):
        self.model.is_running = True
        self.model.stop_requested = False
        self.is_animating = True
        self.active_line_idx = -1 # 重置動畫線條索引，避免殘留上一回的狀態
        self.trigger_animation()

        steps = self.model.current_flow_steps
        python_bin = self.model.python_path # 從 model 讀取路徑
        error_occurred_at = -1 # 追蹤錯誤位置

        startupinfo = None
        if os.name == 'nt': # 僅在 Windows 系統執行
            startupinfo = subprocess.STARTUPINFO()
            # 使用 dwFlags 設定隱藏視窗
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0 # 0 代表 SW_HIDE (隱藏)

        for i in range(self.model.selected_start_idx, len(steps)):
            if self.model.stop_requested: 
                # 提示流程已停止
                self.log_to_view(f"[{time.strftime('%H:%M:%S')}] Step {i} is running, user stop, will take effect from the next step, stop execution step {next_idx + 1} and later process\n")
                self.view.root.after(0, lambda: messagebox.showinfo("Stop", "Process stopped"))
                break
            
            # 檢查前一條線是否被斬斷 (若不是起點)
            if i > 0 and (i-1) in self.model.disabled_lines:
                self.log_to_view(f"[{time.strftime('%H:%M:%S')}] Process stopped at step {i} because the previous line was cut off.\n")
                break

            if i == self.model.selected_start_idx:
                self.active_line_idx = -1
            else:
                self.active_line_idx = i - 1
            
            self.current_step_index = i # 更新目前步驟索引
            self.view.root.after(0, lambda idx=i: self.view.update_node_colors(idx, -1, self.model.selected_start_idx))
            # 視圖自動跟隨目前的節點
            self.view.root.after(0, lambda idx=i: self.view.center_on_node(idx))
            
            try:
                script_path = os.path.join("tasks", f"{steps[i]['module']}.py")
                
                # 使用 -u 開啟無緩衝模式，確保 print 內容即時回傳
                self.current_process = subprocess.Popen(
                    [python_bin, "-u", script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="cp950",
                    errors="replace", # 若解碼失敗，用特殊符號代替而非報錯
                    bufsize=1, # 行緩衝模式
                    startupinfo=startupinfo
                )

                # 讀取輸出
                while True:
                    line = self.current_process.stdout.readline()
                    if not line and self.current_process.poll() is not None:
                        break
                    if line:
                        # 修正：line 本身帶有 \n，strip() 後再由 log_to_view 處理
                        timestamp = time.strftime('%H:%M:%S')
                        self.log_to_view(f"[{timestamp}] {line.strip()}\n")

                return_code = self.current_process.wait()

                if return_code != 0:
                    raise RuntimeError(f"Script execution failed, exit code: {return_code}")
                
            except Exception as e:
                error_occurred_at = i
                timestamp = time.strftime('%H:%M:%S')
                self.log_to_view(f"[{timestamp}] [ERROR] Step {i+1} failed: {str(e)}\n")
                # 立即反應錯誤節點顏色 (紅色)
                self.view.root.after(0, lambda idx=i: self.view.update_node_colors(-1, idx, self.model.selected_start_idx))
                self.view.root.after(0, lambda m=str(e): messagebox.showerror("Error", f"Step {i+1} execution failed:\n{m}"))
                break
        else:
            if not self.model.stop_requested:
                self.view.root.after(0, lambda: messagebox.showinfo("Complete", "Process completed successfully!"))
               
        # 結束後的狀態清理
        self.model.is_running = False
        self.is_animating = False
        self.view.root.after(0, lambda: self.view.btn_run.config(state="normal"))
        self.view.root.after(0, lambda: self.view.toggle_combobox_state(True))
        
        # 修正：只有在沒有錯誤發生時，才重置節點顏色
        if error_occurred_at == -1:
            self.view.root.after(0, lambda: self.view.update_node_colors(-1, -1, self.model.selected_start_idx))