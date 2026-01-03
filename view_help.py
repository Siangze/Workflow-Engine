import tkinter as tk
from tkinter import ttk, scrolledtext
import os
from resource_helper import get_resource_path

class HelpView(tk.Toplevel):
    def __init__(self, parent, manual_text, colors):
        super().__init__(parent)
        self.title("Manual")
        self.geometry("800x600")
        self.colors = colors
        
        # 設定icon
        # Icon 由 root 統一設定，此處移除個別設定
        
        self._setup_ui(manual_text)
        
        # 讓視窗置中即頂層
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self, text):
        self.configure(bg=self.colors["bg"])
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        lbl_title = tk.Label(frame, text="System Manual", font=('Microsoft JhengHei', 18, 'bold'), bg=self.colors["bg"], fg=self.colors["text"])
        lbl_title.pack(anchor="w", pady=(0, 10))

        # 說明書內容顯示區 (唯讀)
        self.text_area = scrolledtext.ScrolledText(
            frame, 
            font=('Microsoft JhengHei', 14), 
            bg=self.colors["bg"], 
            fg=self.colors["text"],
            padx=10, 
            pady=10,
            borderwidth=1,
            relief="solid"
        )
        self.text_area.pack(fill="both", expand=True)
        
        self.text_area.insert(tk.END, text if text else "No manual content available.")
        self.text_area.config(state="disabled") # 設定為唯讀

        btn_close = ttk.Button(frame, text="Close", command=self.destroy, style='big_Button.TButton')
        btn_close.pack(pady=20)

        # 套用樣式
        style = ttk.Style()
        style.configure('TFrame', background=self.colors["bg"])
