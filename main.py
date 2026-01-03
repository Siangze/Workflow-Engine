import tkinter as tk
import os
from model import WorkflowModel
from view import WorkflowView
from presenter import WorkflowPresenter
from resource_helper import get_resource_path

def main():
    root = tk.Tk()
    root.title("Workflow Engine")
    # 設定icon
    icon_path = get_resource_path("./configs/app_icon.png")
    if os.path.exists(icon_path):
        img = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, img)
    root.geometry("1100x750")

    # 初始化 MVP
    presenter = WorkflowPresenter(root)
    model = WorkflowModel()
    view = WorkflowView(root, presenter)
    
    # 建立關聯
    presenter.init_app(model, view)

    root.mainloop()

if __name__ == "__main__":
    main()