import os
import argparse
import time
from PIL import Image
import glymur
import concurrent.futures
import threading
import queue
from tqdm import tqdm

# 创建一个全局队列用于存储转换结果
result_queue = queue.Queue()

# 创建一个锁用于同步输出
print_lock = threading.Lock()

def convert_single_file(input_path, output_path, target_format, quality=None, resize=None):
    """
    转换单个JP2文件到指定格式
    
    参数:
        input_path: 输入文件路径
        output_path: 输出文件路径
        target_format: 目标格式
        quality: 图像质量 (1-100, 仅对jpg/jpeg有效)
        resize: 调整大小 (width, height)
    
    返回:
        (成功标志, 输入路径, 输出路径, 错误信息)
    """
    try:
        # 使用glymur读取JP2文件
        jp2 = glymur.Jp2k(input_path)
        img = Image.fromarray(jp2[:])
        
        # 如果需要调整大小
        if resize and isinstance(resize, tuple) and len(resize) == 2:
            img = img.resize(resize, Image.LANCZOS)
        
        # 保存参数
        save_args = {}
        if quality is not None and target_format.lower() in ['jpg', 'jpeg', 'jpg/jpeg']:
            save_args['quality'] = quality
        
        # 保存为指定格式
        if target_format.lower() in ['jpg', 'jpeg', 'jpg/jpeg']:
            img.save(output_path, format='JPEG', **save_args)
        else:
            img.save(output_path, format=target_format.upper(), **save_args)
        
        return (True, input_path, output_path, None)
    except Exception as e:
        return (False, input_path, output_path, str(e))

def worker(args):
    """
    工作线程函数
    """
    result = convert_single_file(*args)
    result_queue.put(result)
    return result

def convert_jp2_files(input_dir, output_dir, target_format, quality=None, resize=None, max_workers=None, recursive=True):
    """
    递归转换目录中的.jp2文件到指定格式
    
    参数:
        input_dir: 输入目录路径
        output_dir: 输出目录路径
        target_format: 目标格式
        quality: 图像质量 (1-100, 仅对jpg/jpeg有效)
        resize: 调整大小 (width, height)
        max_workers: 最大工作线程数
        recursive: 是否递归处理子目录
    """
    # 收集所有需要转换的文件
    conversion_tasks = []
    total_files = 0
    
    # 遍历目录
    walk_fn = os.walk if recursive else lambda d: [(d, [d for d in os.listdir(d) if os.path.isdir(os.path.join(d, d))], [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))])]
    
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
                conversion_tasks.append((input_path, output_path, target_format, quality, resize))
                total_files += 1
    
    if total_files == 0:
        print("未找到任何JP2文件进行转换")
        return
    
    # 确定工作线程数
    if max_workers is None:
        max_workers = min(32, os.cpu_count() + 4)  # 默认工作线程数
    
    # 创建进度条
    progress_bar = tqdm(total=total_files, desc="转换进度", unit="文件")
    
    # 成功和失败计数
    success_count = 0
    failure_count = 0
    
    # 使用线程池执行转换任务
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = [executor.submit(worker, task) for task in conversion_tasks]
        
        # 启动结果处理线程
        def process_results():
            nonlocal success_count, failure_count
            while True:
                try:
                    success, input_path, output_path, error = result_queue.get(timeout=0.1)
                    progress_bar.update(1)
                    
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                        with print_lock:
                            print(f"\n转换失败: {input_path} - {error}")
                    
                    result_queue.task_done()
                    
                    # 检查是否所有任务都已完成
                    if progress_bar.n >= total_files:
                        break
                except queue.Empty:
                    # 检查是否所有任务都已完成
                    if all(future.done() for future in futures):
                        break
        
        # 启动结果处理线程
        result_thread = threading.Thread(target=process_results)
        result_thread.daemon = True
        result_thread.start()
        
        # 等待所有任务完成
        concurrent.futures.wait(futures)
        result_thread.join()
    
    # 关闭进度条
    progress_bar.close()
    
    # 打印统计信息
    print(f"\n转换完成! 总文件数: {total_files}, 成功: {success_count}, 失败: {failure_count}")
    if failure_count > 0:
        print("请检查上方错误信息以了解失败原因")

def main():
    start_time = time.time()
    
    parser = argparse.ArgumentParser(description='JP2文件格式转换工具')
    parser.add_argument('input_dir', help='输入目录路径')
    parser.add_argument('output_dir', help='输出目录路径')
    parser.add_argument('format', choices=['png', 'jpg/jpeg', 'bmp', 'tiff'], 
                       help='目标格式（png/jpg/jpeg/bmp/tiff）')
    parser.add_argument('-q', '--quality', type=int, choices=range(1, 101), metavar="[1-100]",
                       help='图像质量 (1-100, 仅对jpg/jpeg有效)')
    parser.add_argument('-r', '--resize', nargs=2, type=int, metavar=("WIDTH", "HEIGHT"),
                       help='调整图像大小 (宽度 高度)')
    parser.add_argument('-w', '--workers', type=int, help='工作线程数 (默认为CPU核心数+4)')
    parser.add_argument('-nr', '--no-recursive', action='store_true', 
                       help='不递归处理子目录')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 处理调整大小参数
    resize = tuple(args.resize) if args.resize else None
    
    # 执行转换
    convert_jp2_files(
        args.input_dir, 
        args.output_dir, 
        args.format,
        quality=args.quality,
        resize=resize,
        max_workers=args.workers,
        recursive=not args.no_recursive
    )
    
    # 计算并显示总耗时
    elapsed_time = time.time() - start_time
    print(f"总耗时: {elapsed_time:.2f}秒")

if __name__ == "__main__":
    main()