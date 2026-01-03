import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
from setting import SettingsManager
from resource_helper import get_resource_path
import os

class SettingsView(tk.Toplevel):
    def __init__(self, parent, colors):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("1200x800")
        # 從main取得icon
        self.colors = colors
        self.manager = SettingsManager()
        
        # Icon 由 root 統一設定，此處移除個別設定
        
        # 暫存資料
        self.global_config = self.manager.load_global_config()
        self.flow_config = self.manager.load_flow_config()
        
        self.current_flow_key = None
        self.current_steps = []
        self.is_loading = False # 防止載入資料時觸發 trace

        self._setup_styles()
        self._setup_ui()
        
        # 讓視窗置中即頂層
        self.transient(parent)
        self.grab_set()

    def _setup_styles(self):
        style = ttk.Style()
        # 共用 view.py 的部分樣式，這邊針對 Settings 特有的再定義
        style.configure("Setting.TNotebook", background=self.colors["bg"])
        style.configure("Setting.TFrame", background=self.colors["bg"])
        
        # Tab 樣式
        style.configure("TNotebook.Tab", font=('Microsoft JhengHei', 14, 'bold'), padding=[10, 5])
        
        # Label & Entry
        style.configure("Setting.TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=('Microsoft JhengHei', 14))
        style.configure("Setting.TEntry", padding=5, font=('Microsoft JhengHei', 14))
        # LabelFrame Style
        style.configure("Setting.TLabelframe", background=self.colors["bg"])
        style.configure("Setting.TLabelframe.Label", font=('Microsoft JhengHei', 14, 'bold'), background=self.colors["bg"], foreground=self.colors["text"])

    def _setup_ui(self):
        self.configure(bg=self.colors["bg"])
        
        self.notebook = ttk.Notebook(self, style="Setting.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Tab 1: 全域設定
        self.tab_global = ttk.Frame(self.notebook, style="Setting.TFrame")
        self.notebook.add(self.tab_global, text="General Settings")
        self._setup_global_tab()
        
        # Tab 2: 流程管理
        self.tab_flow = ttk.Frame(self.notebook, style="Setting.TFrame")
        self.notebook.add(self.tab_flow, text="Flow Management")
        self._setup_flow_tab()

    def _setup_global_tab(self):
        frame = ttk.Frame(self.tab_global, style="Setting.TFrame", padding=20)
        frame.pack(fill="both", expand=True)

        # Python Path Section
        path_frame = ttk.Frame(frame, style="Setting.TFrame")
        path_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(path_frame, text="Python Interpreter Path:", style="Setting.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.var_python_path = tk.StringVar(value=self.global_config.get("python_path", ""))
        entry = ttk.Entry(path_frame, textvariable=self.var_python_path, font=('Microsoft JhengHei', 14), width=50)
        entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        
        btn_browse = ttk.Button(path_frame, text="🔎 Browse", command=self._browse_python_path, style='small_Button.TButton')
        btn_browse.grid(row=1, column=1, sticky="w")

        # Manual Editor Section
        ttk.Label(frame, text="Instruction Manual Content:", style="Setting.TLabel").pack(anchor="w", pady=(0, 5))
        
        self.manual_editor = tk.scrolledtext.ScrolledText(
            frame, 
            height=10, 
            font=('Microsoft JhengHei', 14),
            bg="#FFFFFF", 
            fg=self.colors["text"],
            padx=10, 
            pady=10
        )
        self.manual_editor.pack(fill="both", expand=True, pady=(0, 20))
        self.manual_editor.insert(tk.END, self.global_config.get("manual", ""))
        
        # 儲存按鈕
        btn_save = ttk.Button(frame, text="💾 Save", command=self._save_global, style='big_Button.TButton')
        btn_save.pack(anchor="e")

    def _browse_python_path(self):
        path = filedialog.askopenfilename(title="Browse python.exe", filetypes=[("Executable", "*.exe"), ("All Files", "*.*")])
        if path:
            self.var_python_path.set(path)

    def _save_global(self):
        self.global_config["python_path"] = self.var_python_path.get()
        self.global_config["manual"] = self.manual_editor.get("1.0", "end-1c") # 保存說明書內容
        
        if self.manager.save_global_config(self.global_config):
            messagebox.showinfo("Success", "Global settings saved successfully")
        else:
            messagebox.showerror("Error", "Failed to save settings")

    # --- 流程管理 UI 與邏輯 ---

    def _setup_flow_tab(self):
        main_layout = ttk.Frame(self.tab_flow, style="Setting.TFrame", padding=20)
        main_layout.pack(fill="both", expand=True)
        
        # 上方: 選擇流程 / 新增 / 刪除
        top_bar = ttk.Frame(main_layout, style="Setting.TFrame")
        top_bar.pack(fill="x", pady=(0, 20))
        
        ttk.Label(top_bar, text="Select Flow:", style="Setting.TLabel").pack(side="left", padx=(0, 10))
        
        self.combo_flows = ttk.Combobox(top_bar, state="readonly", font=('Microsoft JhengHei', 14), width=30)
        self.combo_flows.pack(side="left", padx=(0, 10))
        self.combo_flows.bind("<<ComboboxSelected>>", self._on_flow_selected)
        
        ttk.Button(top_bar, text="➕ Add Flow", command=self._add_new_flow, style='small_Button.TButton').pack(side="left", padx=5)
        ttk.Button(top_bar, text="➖ Delete Flow", command=self._delete_current_flow, style='small_Button.TButton').pack(side="left", padx=5)
        
        # 流程詳細設定區域
        self.flow_detail_frame = ttk.Frame(main_layout, style="Setting.TFrame")
        self.flow_detail_frame.pack(fill="both", expand=True)
        
        # 標題與描述
        info_frame = ttk.LabelFrame(self.flow_detail_frame, text="Basic Information", padding=10, style="Setting.TLabelframe")
        info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(info_frame, text="Flow Title:", font=('Microsoft JhengHei', 14)).grid(row=0, column=0, sticky="w")
        self.var_flow_title = tk.StringVar()
        self.var_flow_title.trace_add("write", self._sync_flow_data)
        ttk.Entry(info_frame, textvariable=self.var_flow_title, width=40, font=('Microsoft JhengHei', 14)).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(info_frame, text="Description:", font=('Microsoft JhengHei', 14)).grid(row=1, column=0, sticky="w")
        self.var_flow_desc = tk.StringVar()
        self.var_flow_desc.trace_add("write", self._sync_flow_data)
        ttk.Entry(info_frame, textvariable=self.var_flow_desc, width=60, font=('Microsoft JhengHei', 14)).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # 步驟管理 (左右佈局)
        steps_frame = ttk.LabelFrame(self.flow_detail_frame, text="Step Setting", padding=10, style="Setting.TLabelframe")
        steps_frame.pack(fill="both", expand=True)
        
        # 左: Listbox
        list_frame = ttk.Frame(steps_frame)
        list_frame.pack(side="left", fill="y", padx=(0, 20))
        
        self.steps_listbox = tk.Listbox(list_frame, width=30, height=15, font=('Microsoft JhengHei', 14), exportselection=False)
        self.steps_listbox.pack(side="left", fill="y")
        self.steps_listbox.bind("<<ListboxSelect>>", self._on_step_selected)
        
        # 右: 編輯區
        edit_frame = ttk.Frame(steps_frame)
        edit_frame.pack(side="left", fill="both", expand=True)
        
        # 按鈕區 (步驟)
        btn_frame = ttk.Frame(edit_frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(btn_frame, text="➕ Add Step", command=self._add_step, style='small_Button.TButton').pack(side="left", padx=2)
        ttk.Button(btn_frame, text="➖ Delete Step", command=self._delete_step, style='small_Button.TButton').pack(side="left", padx=2)
        ttk.Button(btn_frame, text="💾 Save", command=self._save_current_flow, style='big_Button.TButton').pack(side="right", padx=2)

        # 欄位
        grid_frame = ttk.Frame(edit_frame)
        grid_frame.pack(fill="x")
        
        ttk.Label(grid_frame, text="Step Name:", font=('Microsoft JhengHei', 14)).grid(row=0, column=0, sticky="w", pady=5)
        self.var_step_name = tk.StringVar()
        self.entry_step_name = ttk.Entry(grid_frame, textvariable=self.var_step_name, width=30, font=('Microsoft JhengHei', 14))
        self.entry_step_name.grid(row=0, column=1, sticky="w", pady=5)
        # 綁定即時更新 Listbox 顯示
        self.var_step_name.trace_add("write", self._sync_listbox_name)

        ttk.Label(grid_frame, text="Script Module:", font=('Microsoft JhengHei', 14)).grid(row=1, column=0, sticky="w", pady=5)
        self.var_step_module = tk.StringVar()
        self.var_step_module.trace_add("write", self._sync_step_data)
        self.entry_step_module = ttk.Entry(grid_frame, textvariable=self.var_step_module, width=30, state="readonly", font=('Microsoft JhengHei', 14))
        self.entry_step_module.grid(row=1, column=1, sticky="w", pady=5)
        ttk.Button(grid_frame, text="🔎 Browse", command=self._browse_script, style='small_Button.TButton').grid(row=1, column=2, padx=2)

        ttk.Label(grid_frame, text="Overview:", font=('Microsoft JhengHei', 14)).grid(row=2, column=0, sticky="w", pady=5)
        self.var_step_overview = tk.StringVar()
        self.var_step_overview.trace_add("write", self._sync_step_data)
        ttk.Entry(grid_frame, textvariable=self.var_step_overview, width=50, font=('Microsoft JhengHei', 14)).grid(row=2, column=1, sticky="w", pady=5, columnspan=2)

        self._refresh_flow_list()
        
    def _refresh_flow_list(self):
        flows = list(self.flow_config.keys())
        self.combo_flows['values'] = flows
        
        if self.current_flow_key and self.current_flow_key in flows:
            self.combo_flows.set(self.current_flow_key)
            self._on_flow_selected(None)
        else:
            self.combo_flows.set('')
            self.current_flow_key = None
            self._clear_flow_editor()

    def _clear_flow_editor(self):
        self.is_loading = True
        try:
            self.var_flow_title.set("")
            self.var_flow_desc.set("")
            self.current_steps = []
            self.steps_listbox.delete(0, tk.END)
            self._clear_step_editor()
        finally:
            self.is_loading = False
    
    def _on_flow_selected(self, event):
        key = self.combo_flows.get()
        if not key: return
        
        self.is_loading = True
        try:
            self.current_flow_key = key
            data = self.flow_config[key]
            
            self.var_flow_title.set(data.get("title", ""))
            self.var_flow_desc.set(data.get("description", ""))
            self.current_steps = data.get("steps", [])
            
            self._refresh_steps_listbox()
            self._clear_step_editor()
        finally:
            self.is_loading = False

    def _refresh_steps_listbox(self):
        self.steps_listbox.delete(0, tk.END)
        for step in self.current_steps:
            self.steps_listbox.insert(tk.END, step.get("name", "Unnamed"))

    def _on_step_selected(self, event):
        sel = self.steps_listbox.curselection()
        if not sel: return
        
        self.is_loading = True
        try:
            idx = sel[0]
            step_data = self.current_steps[idx]
            
            self.var_step_name.set(step_data.get("name", ""))
            self.var_step_module.set(step_data.get("module", ""))
            self.var_step_overview.set(step_data.get("overview", ""))
        finally:
            self.is_loading = False

    def _clear_step_editor(self):
        self.var_step_name.set("")
        self.var_step_module.set("")
        self.var_step_overview.set("")

    def _sync_listbox_name(self, *args):
        """當名稱輸入框變動時，更新 Listbox 顯示"""
        if self.is_loading: return
        sel = self.steps_listbox.curselection()
        if not sel: return
        idx = sel[0]
        new_name = self.var_step_name.get()
        self.steps_listbox.delete(idx)
        self.steps_listbox.insert(idx, new_name)
        self.steps_listbox.selection_set(idx)
        # 同步回 current_steps 資料
        self.current_steps[idx]["name"] = new_name

    def _sync_flow_data(self, *args):
        """即時同步流程標題與描述"""
        if self.is_loading or not self.current_flow_key: return
        self.flow_config[self.current_flow_key]["title"] = self.var_flow_title.get()
        self.flow_config[self.current_flow_key]["description"] = self.var_flow_desc.get()

    def _sync_step_data(self, *args):
        """即時同步步驟詳細資料"""
        if self.is_loading: return
        sel = self.steps_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx < len(self.current_steps):
            self.current_steps[idx]["module"] = self.var_step_module.get()
            self.current_steps[idx]["overview"] = self.var_step_overview.get()

    def _add_new_flow(self):
        # 簡單輸入框索取 Key
        key = tk.simpledialog.askstring("Add New Flow", "Please enter the unique identifier (Key) for the new flow:")
        if key:
            if key in self.flow_config:
                messagebox.showerror("Error", "The key already exists")
                return
            self.flow_config[key] = {
                "title": "New Flow",
                "description": "",
                "steps": []
            }
            self.current_flow_key = key
            self._refresh_flow_list()

    def _delete_current_flow(self):
        if not self.current_flow_key: return
        if messagebox.askyesno("Confirmation", f"Are you sure you want to delete flow '{self.current_flow_key}'?"):
            del self.flow_config[self.current_flow_key]
            self.current_flow_key = None
            self._refresh_flow_list()

    def _add_step(self):
        self.current_steps.append({
            "name": "New Step",
            "module": "",
            "overview": ""
        })
        self._refresh_steps_listbox()
        
        # 選取新增的項目
        idx = len(self.current_steps) - 1
        self.steps_listbox.selection_clear(0, tk.END)
        self.steps_listbox.selection_set(idx)
        self.steps_listbox.activate(idx)
        self.steps_listbox.see(idx)
        
        self._on_step_selected(None)

    def _delete_step(self):
        sel = self.steps_listbox.curselection()
        if not sel: return
        idx = sel[0]
        del self.current_steps[idx]
        self._refresh_steps_listbox()
        self._clear_step_editor()

    def _browse_script(self):
        # 確保有選中步驟
        sel = self.steps_listbox.curselection()
        if not sel: 
            messagebox.showwarning("Warning", "Please select a step from the left list first.")
            return

        path = filedialog.askopenfilename(title="Select Python Script", filetypes=[("Python Files", "*.py")])
        if path:
            try:
                module_name = self.manager.import_script(path)
                self.var_step_module.set(module_name)
                
                # 同步回 current_steps
                idx = sel[0]
                self.current_steps[idx]["module"] = module_name
            except Exception as e:
                messagebox.showerror("Import Failed", str(e))
    
    def _save_current_flow(self):
        if not self.current_flow_key: return
        
        # 更新目前選擇到的步驟的所有資料(防止有人改了 Entry 卻沒觸發事件, 雖然有 trace 但保險起見)
        # 補充：trace只綁了name，其他的 module 和 overview 要在這裡確認寫回
        sel = self.steps_listbox.curselection()
        if sel:
            idx = sel[0]
            self.current_steps[idx]["name"] = self.var_step_name.get()
            self.current_steps[idx]["module"] = self.var_step_module.get()
            self.current_steps[idx]["overview"] = self.var_step_overview.get()

        # 更新 flow config 結構
        self.flow_config[self.current_flow_key]["title"] = self.var_flow_title.get()
        self.flow_config[self.current_flow_key]["description"] = self.var_flow_desc.get()
        self.flow_config[self.current_flow_key]["steps"] = self.current_steps
        
        if self.manager.save_flow_config(self.flow_config):
            messagebox.showinfo("Success", "Flow settings saved successfully")
        else:
            messagebox.showerror("Error", "Failed to save settings")
