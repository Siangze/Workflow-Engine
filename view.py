import tkinter as tk
import time, os
from tkinter import scrolledtext
from tkinter import ttk
from ctypes import windll
from resource_helper import get_resource_path

class WorkflowView:
    def __init__(self, root, presenter):
        self.root = root
        self.presenter = presenter
        
        # 色標
        self.colors = {
            "bg": "#FFFFFF", "sidebar": "#F5F5F5", "accent": "#002F6C", "text": "#333333",
            "node_start": "#002F6C", "node_pending": "#00DEB6", "node_finished": "#FFFFFF", 
            "node_running": "#002F6C", "node_skipped": "#E0E0E0", "node_error": "#F78C9C", "line": "#333333"
        } 
        
        self.node_ids = []
        self.text_ids = []
        self.line_ids = []
        self.hover_tooltip = None
        self.dash_offset = 0
        self.cancel_icon_id = None # 取消圖示 ID
        self.hover_line_id = None # 當前 hover 的線段 ID

        self._setup_high_dpi()
        self._apply_styles()
        self.is_welcome_mode = False # 是否在歡迎畫面模式
        self._setup_ui()

    def _setup_high_dpi(self):
        try: windll.shcore.SetProcessDpiAwareness(1)
        except: pass

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=self.colors["bg"])
        style.configure('Sidebar.TFrame', background=self.colors["sidebar"])
        style.configure('TLabel', background=self.colors["bg"], foreground=self.colors["text"], font=('Microsoft JhengHei', 18))
        
        # 下拉選單
        style.configure('TCombobox', font=('Microsoft JhengHei', 18, 'bold'), padding=10, fieldbackground=self.colors['bg'], background=self.colors['bg'])
        style.map('TCombobox', fieldbackground=[('readonly', self.colors['bg'])], selectBackground=[('readonly', self.colors['bg'])], selectForeground=[('readonly', '#FFFFFF')])
        self.root.option_add('*TCombobox*Listbox.background', self.colors['bg'])
        self.root.option_add('*TCombobox*Listbox.foreground', self.colors['text'])
        self.root.option_add('*TCombobox*Listbox.font', ('Microsoft JhengHei', 16))
        
        # 按鈕類
        style.configure('big_Button.TButton', font=('Microsoft JhengHei', 18, 'bold'), foreground=self.colors['bg'], background=self.colors["accent"], padding=10,relief='flat', borderwidth=0)
        style.map('big_Button.TButton', foreground=[('active', self.colors['text'])],background=[('active', '#00DEB6')])
        style.configure('small_Button.TButton', font=('Microsoft JhengHei', 12, 'bold'), foreground=self.colors['bg'], background=self.colors["accent"], padding=5,relief='flat', borderwidth=0)
        style.map('small_Button.TButton', foreground=[('active', self.colors['text'])],background=[('active', '#00DEB6')])
        
        # 隱藏箭頭的垂直捲軸樣式
        style.layout('NoArrow.Vertical.TScrollbar', 
                     [('Vertical.Scrollbar.trough',
                       {'children': [('Vertical.Scrollbar.thumb', 
                                      {'expand': '1', 'sticky': 'nswe'})],
                        'sticky': 'nswe'})])

    
    def _setup_ui(self):
        self.root.configure(bg=self.colors["bg"])
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 初始化縮放倍率
        self.current_zoom = 1.0

        # 側邊欄
        sidebar = ttk.Frame(self.root, style='Sidebar.TFrame', padding=30)
        sidebar.grid(row=0, column=0, sticky="nsew")
        # 加入icon於label左邊
        self.icon = tk.PhotoImage(file=get_resource_path("./configs/icon.png"))
        self.icon = self.icon.subsample(20, 20) # 縮小icon
        ttk.Label(sidebar, text="  Workflow Engine", image=self.icon, compound="left", font=('Microsoft JhengHei', 20, 'bold'), background=self.colors["sidebar"]).pack(anchor="w", pady=(0, 10))
        
        self.combo = ttk.Combobox(sidebar, state="readonly", font=('Microsoft JhengHei', 18, 'bold'), justify='center')
        self.combo.pack(fill="x", pady=(5, 25))
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.presenter.handle_flow_change(self.combo.get()))

        self.msg_desc = tk.Message(sidebar, text="Please select a flow...", width=200, bg=self.colors["sidebar"], fg=self.colors["text"], font=('Microsoft JhengHei', 18))
        self.msg_desc.pack(fill="x", pady=10)

        self.btn_run = ttk.Button(sidebar, text="▶ Start", style='big_Button.TButton', command=self.presenter.handle_run_click)
        self.btn_run.pack(side="bottom", fill="x")
        
        # 畫布與日誌區 (右側)
        right_panel = ttk.Frame(self.root, padding=(0, 0, 40, 40))
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.rowconfigure(0, weight=3) # 畫布比例
        right_panel.rowconfigure(1, weight=1) # 日誌區比例
        right_panel.columnconfigure(0, weight=1)

        # 畫布區
        self.canvas = tk.Canvas(right_panel, bg=self.colors["bg"], highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", pady=(40, 20))
        # 確保畫布可以捲動 (設定捲動範圍，可根據需求調整大小)
        self.canvas.config(scrollregion=(0, 0, 2000, 2000))
        
        # 綁定滑鼠右鍵拖拉
        self.canvas.bind("<Button-3>", self._start_pan) # 右鍵 <Button-3>，中鍵 <Button-2>
        self.canvas.bind("<B3-Motion>", self._do_pan)

        # 綁定滾輪縮放
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.current_zoom = 1.0

        # 在 right_panel 中建立重置按鈕
        self.btn_reset_canvas = ttk.Button(
        right_panel, 
        text="↺", 
        command=self.presenter.handle_reset_click,
        style='small_Button.TButton'
        )
        self.btn_reset_canvas.place(relx=0.98, rely=0.02, x=-50, anchor="ne", width=40, height=40) 

        # 建立中止按鈕 (在重置按鈕右邊)
        self.btn_stop = ttk.Button(
            right_panel,
            text="⏸",
            command=self.presenter.handle_stop_click,
            style='small_Button.TButton'
        )
        self.btn_stop.place(relx=0.98, rely=0.02, anchor="ne", width=40, height=40)

        # 建立設置按鈕 (在重置按鈕左邊)
        self.btn_setting = ttk.Button(
            right_panel,
            text="⚙️",
            command=self.presenter.handle_setting_click,
            style='small_Button.TButton'
        )
        # x=-100 代表從 relx=0.98 的位置往左偏移 100px
        self.btn_setting.place(relx=0.98, rely=0.02, x=-100, anchor="ne", width=40, height=40)

        # 建立說明書按鈕 (在設置按鈕左邊)
        self.btn_help = ttk.Button(
            right_panel,
            text="❓",
            command=self.presenter.handle_help_click,
            style='small_Button.TButton'
        )
        # x=-150 代表從 relx=0.98 的位置往左偏移 150px
        self.btn_help.place(relx=0.98, rely=0.02, x=-150, anchor="ne", width=40, height=40)

        # 執行回饋視窗 (日誌區)
        self.log_area = scrolledtext.ScrolledText(
            right_panel, 
            height=10, 
            font=('Microsoft JhengHei', 12), 
            bg=self.colors["bg"], 
            fg=self.colors["text"],
            padx=15, 
            pady=15,
            borderwidth=1,
            relief="flat"
        )
        self.log_area.grid(row=1, column=0, sticky="nsew")
        self.log_area.config(state="disabled") # 預設唯讀
        
        # 設定捲軸標籤顏色 (選用)
        self.log_area.tag_config("info", foreground="#5D5D5D")
        self.log_area.tag_config("error", foreground=self.colors["node_error"])
        self.log_area.tag_config("success", foreground="#4CAF50")

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        """繪製圓角矩形 (利用 polygon + smooth=True)"""
        points = [
            x1+radius, y1,
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def draw_workflow(self, steps, selected_idx):
        """繪製流程圖"""
        self.canvas.delete("all")
        self.node_ids, self.text_ids, self.line_ids = [], [], []
        x = 250
        for i, step in enumerate(steps):
            y = 100 + (i * 120)
            if i < len(steps) - 1:
                # 檢查是否被禁用
                if i not in self.presenter.model.disabled_lines:
                    line_id = self.canvas.create_line(x, y+35, x, y+85, arrow=tk.LAST, width=4, fill=self.colors["line"])
                    self.line_ids.append(line_id)
                    
                    # 綁定 Hover 事件顯示取消按鈕
                    self.canvas.tag_bind(line_id, "<Enter>", lambda e, lid=i, item_id=line_id: self.show_cancel_icon(lid, item_id))
                    self.canvas.tag_bind(line_id, "<Leave>", lambda e: self.hide_cancel_icon_delayed())
                else:
                    self.line_ids.append(None) # 佔位，保持 index 一致
            
            # 使用圓角矩形，預設半徑 20
            rect = self.create_rounded_rect(x-110, y-30, x+110, y+30, radius=20, fill=self.colors["node_pending"], outline="#333333", width=1)
            text_id = self.canvas.create_text(x, y, text=f"{i+1}. {step['name']}", font=('Microsoft JhengHei', 16), fill=self.colors["text"])
            
            # 綁定事件回傳給 Presenter
            self.canvas.tag_bind(rect, "<Button-1>", lambda e, idx=i: self.presenter.handle_node_click(idx))
            self.canvas.tag_bind(rect, "<Enter>", lambda e, idx=i: self.presenter.handle_hover(e, idx, True))
            self.canvas.tag_bind(rect, "<Leave>", lambda e, idx=i: self.presenter.handle_hover(e, idx, False))
            self.canvas.tag_bind(text_id, "<Button-1>", lambda e, idx=i: self.presenter.handle_node_click(idx))
            
            self.node_ids.append(rect)
            self.text_ids.append(text_id)
        
        # 重繪後重置縮放比例與捲動範圍，避免狀態不同步
        self.current_zoom = 1.0
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        self.update_node_colors(selected_idx, -1, selected_idx)
        
    def show_cancel_icon(self, line_idx, line_item_id):
        """在線段上顯示取消圖示"""
        try:
            coords = self.canvas.coords(line_item_id)
            if not coords: return
            x1, y1, x2, y2 = coords
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
        except:
            return

        if self.cancel_icon_id:
            self.canvas.delete(self.cancel_icon_id)
            
        self.cancel_icon_id = self.canvas.create_text(mid_x + 15, mid_y, text="❌", font=('Arial', 14), fill="red")
        self.canvas.tag_bind(self.cancel_icon_id, "<Button-1>", lambda e: self.presenter.handle_line_cancel(line_idx))
        # 讓滑鼠移到 icon 上也不會消失
        self.canvas.tag_bind(self.cancel_icon_id, "<Enter>", lambda e: self.cancel_hide_timer())
        self.canvas.tag_bind(self.cancel_icon_id, "<Leave>", lambda e: self.hide_cancel_icon_delayed())

    def hide_cancel_icon_delayed(self):
        """延遲隱藏取消圖示"""
        self.hide_timer = self.root.after(300, self._perform_hide_icon)

    def cancel_hide_timer(self):
        """取消隱藏圖示的 Timer"""
        if hasattr(self, 'hide_timer'):
            self.root.after_cancel(self.hide_timer)

    def _perform_hide_icon(self):
        if self.cancel_icon_id:
            self.canvas.delete(self.cancel_icon_id)
            self.cancel_icon_id = None

    def _start_pan(self, event):
        """記錄拖拉起始點"""
        if getattr(self, 'is_welcome_mode', False): return
        self.canvas.scan_mark(event.x, event.y)

    def _do_pan(self, event):
        """執行平移"""
        if getattr(self, 'is_welcome_mode', False): return
        # gain=1 代表 1:1 移動，移動感最自然
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_zoom(self, event):
        """處理畫布放大縮小"""
        if getattr(self, 'is_welcome_mode', False): return
        # 1. 決定縮放比例
        if event.num == 4 or event.delta > 0: # 滾輪向前：放大
            zoom_factor = 1.1
        elif event.num == 5 or event.delta < 0: # 滾輪向後：縮小
            zoom_factor = 0.9
        else:
            return

        # 2. 限制縮放範圍 (避免過大或消失)
        new_zoom = self.current_zoom * zoom_factor
        if not (0.5 < new_zoom < 3.0):
            return
        self.current_zoom = new_zoom

        # 3. 取得目前滑鼠在畫布上的座標 (Canvas Coordinates)
        # 這非常重要，canvasx/y 會考量到目前的捲動偏移量
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        # 4. 對畫布上所有標籤為 "all" 的物件進行縮放
        self.canvas.scale("all", x, y, zoom_factor, zoom_factor)
        
        # 5. 更新捲動範圍，確保縮放後拖拉依然正常
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def reset_view_state(self):
        """將畫布視角歸零"""
        self.current_zoom = 1.0
        # 強制重置 scrollregion，避免之前的 zoom 或 pan 導致視角定位偏移
        self.canvas.config(scrollregion=(0, 0, 2000, 2000))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        # 重設縮放變換，最安全的方法是清空後由 presenter 觸發重繪
        self.canvas.delete("all")
        self.clear_log() # 清空Log

    def update_node_colors(self, current_idx, error_idx, start_idx):
        """更新節點顏色"""
        # 定義狀態顏色: (背景, 文字)
        STATUS_COLORS = {
            "start": (self.colors["node_start"], "#FFFFFF"),
            "running": (self.colors["node_running"], "#FFFFFF"),
            "finished": (self.colors["node_finished"], self.colors["text"]),
            "pending": (self.colors["node_pending"], self.colors["text"]),
            "skipped": (self.colors["node_skipped"], "#999999"),
            "error": (self.colors["node_error"], "#FFFFFF")
        }

        for i, rect in enumerate(self.node_ids):
            bg_color, txt_color = STATUS_COLORS["pending"] # 預設

            if i == error_idx: 
                bg_color, txt_color = STATUS_COLORS["error"]
            elif i == current_idx: 
                bg_color, txt_color = STATUS_COLORS["running"]
            elif i < start_idx: 
                bg_color, txt_color = STATUS_COLORS["skipped"]
            elif i < current_idx and current_idx != -1: # i 在 start與current之間 -> Finished
                bg_color, txt_color = STATUS_COLORS["finished"]
            elif i == start_idx and current_idx == -1: # 還沒開始 -> Start
                bg_color, txt_color = STATUS_COLORS["start"]
            else:
                bg_color, txt_color = STATUS_COLORS["pending"]
            
            self.canvas.itemconfig(rect, fill=bg_color, outline="#F5F5F5", width=1)
            # 更新對應的文字顏色
            if i < len(self.text_ids):
                self.canvas.itemconfig(self.text_ids[i], fill=txt_color)

    def center_on_node(self, node_idx):
        """將視角移動到指定節點，並保持置中"""
        if node_idx < 0 or node_idx >= len(self.node_ids): return
        
        # 1. 取得目標節點的邊界框 (bbox 會自動考慮目前的 zoom)
        rect_id = self.node_ids[node_idx]
        bbox = self.canvas.bbox(rect_id) # (x1, y1, x2, y2)
        if not bbox: return
        
        node_center_x = (bbox[0] + bbox[2]) / 2
        node_center_y = (bbox[1] + bbox[3]) / 2

        # 2. 取得目前畫布的可視區域大小
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 3. 取得目前的捲動範圍 (scrollregion)
        sr = self.canvas.config("scrollregion")[4]
        if not sr: return
        sr = [float(x) for x in sr.split()] # x1, y1, x2, y2
        sr_width = sr[2] - sr[0]
        sr_height = sr[3] - sr[1]
        
        if sr_width == 0 or sr_height == 0: return

        # 4. 計算要捲動到的目標位置 (fraction 0.0 ~ 1.0)
        # 目標: 讓 node_center 位於視窗正中央
        # view_left = node_center - (canvas_width / 2)
        target_left = node_center_x - (canvas_width / 2)
        target_top = node_center_y - (canvas_height / 2)

        # 5. 轉換成比例 (相對於 scrollregion) (需扣除 sr 起始偏移)
        x_fraction = (target_left - sr[0]) / sr_width
        y_fraction = (target_top - sr[1]) / sr_height
        
        # 6. 執行捲動
        self.canvas.xview_moveto(x_fraction)
        self.canvas.yview_moveto(y_fraction)

    def animate_lines_step(self, active_line_idx, is_animating):
        """流程線設定"""
        if not is_animating:
            for lid in self.line_ids:
                self.canvas.itemconfig(lid, dash=(), width=1, fill=self.colors["line"])
            return
        
        self.dash_offset = (self.dash_offset + 1) % 20
        if 0 <= active_line_idx < len(self.line_ids):
            line_id = self.line_ids[active_line_idx]
            self.canvas.itemconfig(line_id, dash=(8, 4), dashoffset=self.dash_offset, fill=self.colors["accent"], width=4)
        self.root.after(50, lambda: self.presenter.trigger_animation())

    def show_tooltip(self, event, text=None):
        """顯示 Tooltip"""
        if self.hover_tooltip:
            self.hover_tooltip.destroy()
            self.hover_tooltip = None
        if text:
            x, y = event.x_root + 20, event.y_root + 10
            self.hover_tooltip = tk.Toplevel(self.root)
            self.hover_tooltip.wm_overrideredirect(True)
            self.hover_tooltip.wm_geometry(f"+{x}+{y}")
            tk.Label(self.hover_tooltip, text=text, bg=self.colors["text"], fg="#FFFFFF", padx=12, pady=8, font=('Microsoft JhengHei', 14)).pack()

    def write_log(self, message):
        """更新 Log 的方法"""
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message)
        self.log_area.see(tk.END) # 自動捲動到底部
        self.log_area.config(state="disabled")

    def clear_log(self):
        """清空 Log 區域"""
        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")

    def toggle_combobox_state(self, enabled):
        """切換下拉選單狀態 (避免執行時被修改)"""
        state = "readonly" if enabled else "disabled"
        self.combo.config(state=state)

    def start_welcome_animation(self):
        """開始歡迎畫面動畫"""
        self.stop_welcome_animation() # 確保先停止舊的
        self.is_welcome_mode = True
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0,0,1,1)) # 鎖定捲動

        # 初始繪製 (位置稍後由 OnResize 修正)
        cx, cy = 0, 0

        if hasattr(self, 'icon'):
            self.welcome_icon_id = self.canvas.create_image(cx, cy - 20, image=self.icon)
        
        self.welcome_text_id = self.canvas.create_text(
            cx, cy + 50, 
            text="Workflow Engine", 
            font=('Microsoft JhengHei', 36, 'bold'), 
            fill=self.colors["accent"]
        )

        # 綁定大小改變事件以即時置中
        self.welcome_resize_bind = self.canvas.bind("<Configure>", self._on_welcome_resize)
        
        self.welcome_step = 0
        self._animate_welcome_step()

    def stop_welcome_animation(self):
        """停止歡迎畫面動畫"""
        self.is_welcome_mode = False
        if hasattr(self, 'welcome_anim_id') and self.welcome_anim_id:
            self.root.after_cancel(self.welcome_anim_id)
            self.welcome_anim_id = None
        
        if hasattr(self, 'welcome_resize_bind'):
            self.canvas.unbind("<Configure>", self.welcome_resize_bind)
            del self.welcome_resize_bind

        self.canvas.delete("all")

    def _on_welcome_resize(self, event):
        """當畫布大小改變時，重新置中歡迎畫面元素"""
        cx, cy = event.width / 2, event.height / 2
        if hasattr(self, 'welcome_text_id'):
            self.canvas.coords(self.welcome_text_id, cx, cy + 50)
        if hasattr(self, 'welcome_icon_id'):
            self.canvas.coords(self.welcome_icon_id, cx, cy - 20)

    def _animate_welcome_step(self):
        """呼吸燈效果"""
        # 使用 sin 波產生 0~1 之間的係數
        import math
        alpha = (math.sin(self.welcome_step * 0.1) + 1) / 2 # 0.0 ~ 1.0
        
        c1 = self.colors["accent"] 
        c2 = "#6699CC"             
        
        def hex_to_rgb(hex_val):
            return tuple(int(hex_val.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(rgb):
            return '#%02x%02x%02x' % tuple(int(x) for x in rgb)

        rgb1 = hex_to_rgb(c1)
        rgb2 = hex_to_rgb(c2)
        
        new_rgb = [
            rgb1[0] + (rgb2[0] - rgb1[0]) * alpha,
            rgb1[1] + (rgb2[1] - rgb1[1]) * alpha,
            rgb1[2] + (rgb2[2] - rgb1[2]) * alpha
        ]
        
        new_color = rgb_to_hex(new_rgb)
        self.canvas.itemconfig(self.welcome_text_id, fill=new_color)

        self.welcome_step += 1
        self.welcome_anim_id = self.root.after(50, self._animate_welcome_step)