import sys
import os

def get_resource_path(relative_path):
    """
    取得資源檔案的絕對路徑。
    
    支援兩種模式：
    1. 開發模式：直接從相對路徑讀取 (例如 configs/icon.png)
    2. 打包模式 (PyInstaller)：從 sys._MEIPASS 下的 internal 資料夾讀取
    
    Args:
        relative_path (str): 相對路徑，例如 "configs/icon.png"
    
    Returns:
        str: 檔案的絕對路徑
    """
    
    # 判斷是否為 PyInstaller 打包環境
    if hasattr(sys, '_MEIPASS'):
        # 打包後，檔案被解壓到 sys._MEIPASS
        # 根據 build.bat 設定，我們將 configs/*.png 放到 internal/ 下
        # 所以如果輸入 "configs/icon.png"，我們要轉成 "internal/icon.png"
        
        filename = os.path.basename(relative_path)
        base_path = os.path.join(sys._MEIPASS, "internal")
        return os.path.join(base_path, filename)
    else:
        # 開發環境，直接使用原始路徑
        return os.path.abspath(relative_path)
