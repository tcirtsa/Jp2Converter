import os
import sys
import tkinter as tk
from tkinter import ttk, font
import ttkthemes

def _fix_button_style(button):
    """修复按钮样式，确保在Windows环境下正确显示"""
    style = button.cget('style')
    if style in ['Primary.TButton', 'Secondary.TButton', 'Danger.TButton']:
        # 强制更新按钮样式
        button.update_idletasks()
        # 确保按钮可见
        button.configure(default='normal')
        # 增加按钮边框和对比度
        button.configure(width=15)

def apply_modern_theme(root):
    """应用现代化主题到应用程序"""
    # 尝试使用ttkthemes库应用主题
    try:
        # 如果ttkthemes库不存在，尝试安装
        try:
            import ttkthemes
        except ImportError:
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "ttkthemes"])
            import ttkthemes
        
        # 应用主题
        style = ttkthemes.ThemedStyle(root)
        style.set_theme("arc")
        
        # 自定义样式
        customize_styles(style)
        
        return True
    except Exception as e:
        print(f"应用主题失败: {e}")
        # 如果ttkthemes失败，应用自定义样式
        style = ttk.Style()
        customize_styles(style)
        return False

def customize_styles(style):
    """自定义控件样式"""
    # 设置字体
    default_font = font.nametofont("TkDefaultFont")
    default_font.configure(size=12)  # 增加默认字体大小
    text_font = font.nametofont("TkTextFont")
    text_font.configure(size=12)  # 增加文本字体大小
    
    # 基本按钮样式 - 使用ttk支持的属性
    style.configure('TButton', padding=10, font=('', 12), relief='raised', borderwidth=2)
    # 添加按钮悬停效果
    style.map('TButton',
              foreground=[('active', '#000000'), ('pressed', '#000000')],
              background=[('active', '#e6e6e6'), ('pressed', '#d9d9d9')],
              relief=[('pressed', 'sunken')])
    
    # 标签框样式
    style.configure('TLabelframe', padding=8, relief="groove", borderwidth=1)
    style.configure('TLabelframe.Label', font=('', 12, 'bold'))  # 增加标签框字体大小
    
    # 标签样式
    style.configure('TLabel', padding=2, font=('', 12))  # 增加标签字体大小
    
    # 输入框样式
    style.configure('TEntry', padding=5, font=('', 12))  # 增加输入框字体大小
    
    # 进度条样式
    style.configure("TProgressbar", thickness=20)
    
    # 下拉框样式
    style.configure('TCombobox', padding=5, font=('', 12))  # 增加下拉框字体大小
    
    # 复选框样式
    style.configure('TCheckbutton', padding=5, font=('', 12))  # 增加复选框字体大小
    
    # 选项卡样式
    style.configure('TNotebook', padding=5)
    style.configure('TNotebook.Tab', padding=[10, 5], font=('', 12))  # 增加选项卡字体大小
    
    # 自定义样式
    style.configure('Header.TLabel', font=('', 14, 'bold'))  # 增加标题字体大小
    style.configure('Success.TLabel', foreground='green', font=('', 12))  # 增加成功标签字体大小
    style.configure('Error.TLabel', foreground='red', font=('', 12))  # 增加错误标签字体大小
    style.configure('Status.TLabel', font=('', 11))  # 增加状态标签字体大小
    
    # 主按钮样式 - 蓝色
    style.configure('Primary.TButton', 
                   font=('', 12, 'bold'), 
                   padding=10, 
                   background='#4a7a8c', 
                   foreground='black',
                   borderwidth=3,
                   relief='raised')
    style.map('Primary.TButton',
              foreground=[('active', 'black'), ('pressed', 'black')],
              background=[('active', '#5a8a9c'), ('pressed', '#2c5d6e')],
              relief=[('pressed', 'sunken')])
    
    # 次要按钮样式 - 灰色
    style.configure('Secondary.TButton', 
                   font=('', 12), 
                   padding=10, 
                   background='#6c757d', 
                   foreground='black',
                   borderwidth=3,
                   relief='raised')
    style.map('Secondary.TButton',
              foreground=[('active', 'black'), ('pressed', 'black')],
              background=[('active', '#7c858d'), ('pressed', '#5a6268')],
              relief=[('pressed', 'sunken')])
    
    # 危险按钮样式 - 红色
    style.configure('Danger.TButton', 
                   font=('', 12), 
                   padding=10, 
                   background='#dc3545', 
                   foreground='black',
                   borderwidth=3,
                   relief='raised')
    style.map('Danger.TButton',
              foreground=[('active', 'black'), ('pressed', 'black')],
              background=[('active', '#e04555'), ('pressed', '#c82333')],
              relief=[('pressed', 'sunken')])
    
    # 确保Windows下按钮样式正确显示
    if sys.platform == 'win32':
        # 增强Windows下按钮的可见性
        style.configure('Primary.TButton', background='#2980b9', foreground='black')
        style.configure('Secondary.TButton', background='#7f8c8d', foreground='black')
        style.configure('Danger.TButton', background='#e74c3c', foreground='black')

def customize_text_widget(text_widget):
    """自定义文本控件样式"""
    text_widget.configure(
        background="#f8f9fa",
        foreground="#212529",
        selectbackground="#4a7a8c",
        selectforeground="white",
        padx=10,
        pady=5,
        font=("Consolas", 12)  # 增加字体大小
    )
    
    # 添加标签样式
    text_widget.tag_configure("success", foreground="#28a745")
    text_widget.tag_configure("error", foreground="#dc3545")
    text_widget.tag_configure("warning", foreground="#ffc107")
    text_widget.tag_configure("info", foreground="#17a2b8")
    text_widget.tag_configure("bold", font=("Consolas", 12, "bold"))  # 增加粗体字体大小

def set_window_icon(root, icon_path="icon.ico"):
    """设置窗口图标"""
    try:
        root.iconbitmap(icon_path)
    except:
        pass

def center_window(root, width=800, height=600):
    """将窗口居中显示"""
    # 获取屏幕尺寸
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # 计算居中位置
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    # 设置窗口位置
    root.geometry(f"{width}x{height}+{x}+{y}")