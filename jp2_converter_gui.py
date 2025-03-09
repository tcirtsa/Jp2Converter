import os
import sys
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import concurrent.futures

# 导入原始转换器模块的功能
from jp2_converter import convert_single_file

# 导入主题模块
from theme import apply_modern_theme, customize_text_widget, center_window

class JP2ConverterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("JP2 格式转换工具")
        
        # 应用现代主题
        apply_modern_theme(self)
        
        # 设置窗口大小并居中
        center_window(self, 900, 850)
        self.resizable(True, True)
        
        # 设置应用程序图标
        try:
            self.iconbitmap("icon.ico")
        except:
            pass
        
        # 初始化变量
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.target_format = tk.StringVar(value="jpg")
        self.quality = tk.IntVar(value=90)
        self.resize_width = tk.IntVar(value=0)
        self.resize_height = tk.IntVar(value=0)
        # 设置最大线程数为CPU核心数的两倍（但不超过64）
        cpu_count = os.cpu_count()
        max_recommended = min(64, cpu_count * 2) if cpu_count else 32
        self.max_workers = tk.IntVar(value=max_recommended)
        self.recursive = tk.BooleanVar(value=True)
        
        # 转换状态变量
        self.is_converting = False
        self.is_paused = False
        self.conversion_tasks = []
        self.total_files = 0
        self.success_count = 0
        self.failure_count = 0
        self.current_task_index = 0
        
        # 创建队列用于存储转换结果
        self.result_queue = queue.Queue()
        
        # 创建线程池
        self.executor = None
        self.futures = []
        self.result_thread = None
        
        # 创建UI组件
        self.create_widgets()
        
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建选项卡控件
        tab_control = ttk.Notebook(main_frame)
        
        # 创建选项卡页面
        settings_tab = ttk.Frame(tab_control)
        advanced_tab = ttk.Frame(tab_control)
        
        tab_control.add(settings_tab, text="基本设置")
        tab_control.add(advanced_tab, text="高级设置")
        tab_control.pack(fill=tk.BOTH, expand=True)
        
        # 基本设置选项卡
        self.create_settings_tab(settings_tab)
        
        # 高级设置选项卡
        self.create_advanced_tab(advanced_tab)
        
        # 创建进度显示区域
        progress_frame = ttk.LabelFrame(main_frame, text="转换进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=10)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # 状态标签
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.X)
        
        ttk.Label(status_frame, text="状态:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="总文件数:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.total_files_label = ttk.Label(status_frame, text="0")
        self.total_files_label.grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="已完成:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.completed_files_label = ttk.Label(status_frame, text="0")
        self.completed_files_label.grid(row=1, column=3, sticky=tk.W)
        
        ttk.Label(status_frame, text="成功:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.success_files_label = ttk.Label(status_frame, text="0", style="Success.TLabel")
        self.success_files_label.grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="失败:").grid(row=2, column=2, sticky=tk.W, padx=5)
        self.failed_files_label = ttk.Label(status_frame, text="0", style="Error.TLabel")
        self.failed_files_label.grid(row=2, column=3, sticky=tk.W)
        
        ttk.Label(status_frame, text="耗时:").grid(row=3, column=0, sticky=tk.W, padx=5)
        self.elapsed_time_label = ttk.Label(status_frame, text="0秒")
        self.elapsed_time_label.grid(row=3, column=1, sticky=tk.W)
        
        # 创建日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 日志文本框
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 应用自定义样式到文本控件
        customize_text_widget(self.log_text)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 创建按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 开始按钮 - 增加宽度和高度
        self.start_button = ttk.Button(button_frame, text="开始转换", command=self.start_conversion, style="Primary.TButton", width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 暂停按钮 - 增加宽度和高度
        self.pause_button = ttk.Button(button_frame, text="暂停", command=self.pause_conversion, state=tk.DISABLED, style="Secondary.TButton", width=15)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮 - 增加宽度和高度
        self.cancel_button = ttk.Button(button_frame, text="取消", command=self.cancel_conversion, state=tk.DISABLED, style="Danger.TButton", width=15)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        # 退出按钮 - 增加宽度和高度
        self.exit_button = ttk.Button(button_frame, text="退出", command=self.on_closing, style="Secondary.TButton", width=15)
        self.exit_button.pack(side=tk.RIGHT, padx=5)
        
        # 修复按钮样式
        from theme import _fix_button_style
        _fix_button_style(self.start_button)
        _fix_button_style(self.pause_button)
        _fix_button_style(self.cancel_button)
        _fix_button_style(self.exit_button)
    
    def create_settings_tab(self, parent):
        # 创建输入目录选择
        input_frame = ttk.Frame(parent, padding="5")
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="输入目录:").pack(side=tk.LEFT)
        input_entry = ttk.Entry(input_frame, textvariable=self.input_dir, width=50)
        input_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        browse_input_button = ttk.Button(input_frame, text="浏览...", command=self.browse_input_dir)
        browse_input_button.pack(side=tk.LEFT)
        
        # 创建输出目录选择
        output_frame = ttk.Frame(parent, padding="5")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="输出目录:").pack(side=tk.LEFT)
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir, width=50)
        output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        browse_output_button = ttk.Button(output_frame, text="浏览...", command=self.browse_output_dir)
        browse_output_button.pack(side=tk.LEFT)
        
        # 创建格式选择
        format_frame = ttk.Frame(parent, padding="5")
        format_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(format_frame, text="目标格式:").pack(side=tk.LEFT)
        
        formats = ["jpg", "jpeg", "png", "bmp", "tiff"]
        format_combobox = ttk.Combobox(format_frame, textvariable=self.target_format, values=formats, state="readonly", width=10)
        format_combobox.pack(side=tk.LEFT, padx=5)
        
        # 递归处理选项
        recursive_check = ttk.Checkbutton(format_frame, text="递归处理子目录", variable=self.recursive)
        recursive_check.pack(side=tk.RIGHT, padx=5)
    
    def create_advanced_tab(self, parent):
        # 质量设置（对JPEG有效）
        quality_frame = ttk.Frame(parent, padding="5")
        quality_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(quality_frame, text="图像质量 (1-100, 仅对JPEG有效):").pack(side=tk.LEFT)
        quality_spinbox = ttk.Spinbox(quality_frame, from_=1, to=100, textvariable=self.quality, width=5)
        quality_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 调整大小设置
        resize_frame = ttk.Frame(parent, padding="5")
        resize_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(resize_frame, text="调整大小 (0表示保持原始大小):").pack(side=tk.LEFT)
        ttk.Label(resize_frame, text="宽度:").pack(side=tk.LEFT, padx=(10, 0))
        width_spinbox = ttk.Spinbox(resize_frame, from_=0, to=10000, textvariable=self.resize_width, width=6)
        width_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(resize_frame, text="高度:").pack(side=tk.LEFT)
        height_spinbox = ttk.Spinbox(resize_frame, from_=0, to=10000, textvariable=self.resize_height, width=6)
        height_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 线程数设置
        workers_frame = ttk.Frame(parent, padding="5")
        workers_frame.pack(fill=tk.X, pady=5)
        
        # 获取CPU核心数
        cpu_count = os.cpu_count()
        max_recommended = min(64, cpu_count * 2) if cpu_count else 32
        
        ttk.Label(workers_frame, text="工作线程数:").pack(side=tk.LEFT)
        self.workers_spinbox = ttk.Spinbox(workers_frame, from_=1, to=max_recommended, textvariable=self.max_workers, width=5)
        self.workers_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 添加说明标签
        ttk.Label(workers_frame, text=f"(推荐值: {max_recommended}, 暂停时可修改)").pack(side=tk.LEFT, padx=5)
    
    def browse_input_dir(self):
        directory = filedialog.askdirectory(title="选择输入目录")
        if directory:
            self.input_dir.set(directory)
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
    
    def log(self, message, tag=None):
        """添加日志消息到日志文本框"""
        # 获取当前时间
        current_time = time.strftime("%H:%M:%S", time.localtime())
        
        # 构建带时间戳的消息
        log_message = f"[{current_time}] {message}\n"
        
        # 插入消息
        self.log_text.insert(tk.END, log_message)
        
        # 如果指定了标签，应用标签样式
        if tag and tag in ["success", "error", "warning", "info", "bold"]:
            # 计算新插入文本的起始和结束位置
            start_pos = self.log_text.index(f"end-{len(log_message)+1}c")
            end_pos = self.log_text.index("end-1c")
            
            # 应用标签
            self.log_text.tag_add(tag, start_pos, end_pos)
        
        # 自动滚动到最新消息
        self.log_text.see(tk.END)
    
    def update_status(self):
        completed = self.success_count + self.failure_count
        self.progress_var.set((completed / self.total_files) * 100 if self.total_files > 0 else 0)
        
        self.total_files_label.config(text=str(self.total_files))
        self.completed_files_label.config(text=str(completed))
        self.success_files_label.config(text=str(self.success_count))
        self.failed_files_label.config(text=str(self.failure_count))
        
        elapsed = time.time() - self.start_time
        self.elapsed_time_label.config(text=f"{elapsed:.2f}秒")
        
        # 更新状态标签
        if self.is_paused:
            self.status_label.config(text="已暂停")
        elif self.is_converting:
            self.status_label.config(text="正在转换...")
        else:
            self.status_label.config(text="就绪")
    
    def collect_tasks(self):
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        target_format = self.target_format.get()
        quality = self.quality.get()
        recursive = self.recursive.get()
        if not input_dir or not os.path.isdir(input_dir):
            messagebox.showerror("错误", "请选择有效的输入目录")
            return None, 0
        
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return None, 0
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 收集所有需要转换的文件
        conversion_tasks = []
        total_files = 0
        
        # 遍历目录
        walk_fn = os.walk if recursive else lambda d: [(d, [d for d in os.listdir(d) if os.path.isdir(os.path.join(d, d))], [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))])]
        
        self.log(f"开始扫描目录: {input_dir}")
        for root, dirs, files in walk_fn(input_dir):
            # 创建对应的输出目录结构
            relative_path = os.path.relpath(root, input_dir)
            output_subdir = os.path.join(output_dir, relative_path)
            os.makedirs(output_subdir, exist_ok=True)

            for file in files:
                if file.lower().endswith('.jp2'):
                    input_path = os.path.join(root, file)
                    output_filename = os.path.splitext(file)[0] + '.' + target_format.lower()
                    output_path = os.path.join(output_subdir, output_filename)
                    
                    # 添加到任务列表
                    resize = None
                    if self.resize_width.get() > 0 and self.resize_height.get() > 0:
                        resize = (self.resize_width.get(), self.resize_height.get())
                    
                    conversion_tasks.append((input_path, output_path, target_format, quality, resize))
                    total_files += 1
        
        self.log(f"扫描完成，找到 {total_files} 个JP2文件")
        return conversion_tasks, total_files
    
    def process_results(self):
        while not self.is_converting and not self.result_queue.empty():
            # 清空队列中的剩余结果
            try:
                self.result_queue.get(block=False)
                self.result_queue.task_done()
            except queue.Empty:
                break
        
        while self.is_converting:
            try:
                # 检查是否暂停
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                # 从队列获取结果
                success, input_path, output_path, error = self.result_queue.get(timeout=0.1)
                
                if success:
                    self.success_count += 1
                    self.log(f"转换成功: {os.path.basename(input_path)}")
                else:
                    self.failure_count += 1
                    self.log(f"转换失败: {os.path.basename(input_path)} - {error}")
                
                self.result_queue.task_done()
                
                # 更新UI
                self.update_status()
                
                # 检查是否所有任务都已完成
                completed = self.success_count + self.failure_count
                if completed >= self.total_files:
                    self.log("所有任务已完成")
                    self.finish_conversion()
                    break
            except queue.Empty:
                # 检查是否所有任务都已完成
                if self.executor is None or all(future.done() for future in self.futures):
                    completed = self.success_count + self.failure_count
                    if completed >= self.total_files:
                        self.log("所有任务已完成")
                        self.finish_conversion()
                    break
            except Exception as e:
                self.log(f"处理结果时出错: {str(e)}")
    
    def start_conversion(self):
        # 检查是否已经在转换中
        if self.is_converting and not self.is_paused:
            return
        
        # 如果是从暂停状态恢复
        if self.is_paused:
            self.resume_conversion()
            return
        
        # 收集转换任务
        self.conversion_tasks, self.total_files = self.collect_tasks()
        
        if self.total_files == 0:
            messagebox.showinfo("提示", "未找到任何JP2文件进行转换")
            return
        
        # 重置计数器
        self.success_count = 0
        self.failure_count = 0
        self.current_task_index = 0
        self.start_time = time.time()
        
        # 更新UI状态
        self.is_converting = True
        self.is_paused = False
        self.start_button.config(text="继续", state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.NORMAL)
        self.workers_spinbox.config(state=tk.DISABLED)
        
        # 创建线程池
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers.get())
        
        # 提交所有任务
        self.log(f"开始转换，使用 {self.max_workers.get()} 个工作线程")
        self.futures = [self.executor.submit(self.worker, task) for task in self.conversion_tasks]
        
        # 启动结果处理线程
        self.result_thread = threading.Thread(target=self.process_results)
        self.result_thread.daemon = True
        self.result_thread.start()
        
        # 定时更新UI
        self.update_status()
        self.after(100, self.update_ui)
    
    def worker(self, args):
        # 检查是否暂停
        while self.is_paused and self.is_converting:
            time.sleep(0.1)
        
        # 如果已取消，则不执行任务
        if not self.is_converting:
            return None
        
        # 执行转换
        result = convert_single_file(*args)
        self.result_queue.put(result)
        return result
    
    def pause_conversion(self):
        if not self.is_converting or self.is_paused:
            return
        
        self.is_paused = True
        self.start_button.config(text="继续", state=tk.NORMAL)
        self.pause_button.config(text="已暂停", state=tk.DISABLED)
        self.workers_spinbox.config(state=tk.NORMAL)
        
        self.log("转换已暂停，可以修改线程数量")
        self.update_status()
    
    def resume_conversion(self):
        if not self.is_converting or not self.is_paused:
            return
        
        # 检查是否修改了线程数
        new_max_workers = self.max_workers.get()
        if new_max_workers != len(self.futures) and self.executor is not None:
            self.log(f"线程数已更改为 {new_max_workers}")
            
            # 关闭旧的线程池
            old_executor = self.executor
            old_futures = self.futures
            
            # 创建新的线程池
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=new_max_workers)
            
            # 重新提交未完成的任务
            remaining_tasks = []
            for i, future in enumerate(old_futures):
                if not future.done() and not future.running():
                    remaining_tasks.append(self.conversion_tasks[i])
            
            self.futures = [self.executor.submit(self.worker, task) for task in remaining_tasks]
            
            # 关闭旧的线程池（不会中断正在执行的任务）
            old_executor.shutdown(wait=False)
        
        self.is_paused = False
        self.start_button.config(text="开始转换", state=tk.DISABLED)
        self.pause_button.config(text="暂停", state=tk.NORMAL)
        self.workers_spinbox.config(state=tk.DISABLED)
        
        self.log("转换已恢复")
        self.update_status()
    
    def cancel_conversion(self):
        if not self.is_converting:
            return
        
        if messagebox.askyesno("确认", "确定要取消当前转换任务吗？"):
            self.is_converting = False
            self.is_paused = False
            
            # 关闭线程池
            if self.executor is not None:
                self.executor.shutdown(wait=False)
                self.executor = None
            
            # 重置UI状态
            self.start_button.config(text="开始转换", state=tk.NORMAL)
            self.pause_button.config(text="暂停", state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            self.workers_spinbox.config(state=tk.NORMAL)
            
            self.log("转换已取消")
            self.update_status()
    
    def finish_conversion(self):
        self.is_converting = False
        self.is_paused = False
        
        # 关闭线程池
        if self.executor is not None:
            self.executor.shutdown(wait=True)
            self.executor = None
        
        # 重置UI状态
        self.start_button.config(text="开始转换", state=tk.NORMAL)
        self.pause_button.config(text="暂停", state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
        self.workers_spinbox.config(state=tk.NORMAL)
        
        # 计算总耗时
        elapsed_time = time.time() - self.start_time
        
        # 显示完成信息
        self.log(f"\n转换完成! 总文件数: {self.total_files}, 成功: {self.success_count}, 失败: {self.failure_count}")
        self.log(f"总耗时: {elapsed_time:.2f}秒")
        
        if self.failure_count > 0:
            self.log("请查看上方日志了解失败原因")
        
        # 显示完成对话框
        messagebox.showinfo("完成", f"转换已完成!\n总文件数: {self.total_files}\n成功: {self.success_count}\n失败: {self.failure_count}\n总耗时: {elapsed_time:.2f}秒")
    
    def update_ui(self):
        if self.is_converting:
            self.update_status()
            self.after(100, self.update_ui)
    
    def on_closing(self):
        if self.is_converting:
            if not messagebox.askyesno("确认", "转换任务正在进行中，确定要退出吗？"):
                return
            
            # 取消转换
            self.is_converting = False
            if self.executor is not None:
                self.executor.shutdown(wait=False)
        
        self.destroy()

def main():
    app = JP2ConverterGUI()
    app.mainloop()

if __name__ == "__main__":
    main()