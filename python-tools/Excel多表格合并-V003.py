import pandas as pd
import os
import hashlib
import time
import sys
import math

class ProgressBar:
    def __init__(self, total, prefix='', suffix='', length=50, fill='█'):
        """
        进度条显示类
        
        参数:
        total: 总项目数
        prefix: 前缀文本
        suffix: 后缀文本
        length: 进度条长度(字符)
        fill: 进度填充字符
        """
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.length = length
        self.fill = fill
        self.start_time = time.time()
        self.completed = 0
        self._update(0)
    
    def _update(self, iteration):
        """更新进度显示"""
        self.completed = iteration
        percent = f"{100 * (iteration / float(self.total)):.1f}"
        filled_length = int(self.length * iteration // self.total)
        bar = self.fill * filled_length + '-' * (self.length - filled_length)
        
        # 计算时间信息
        elapsed = time.time() - self.start_time
        if iteration > 0 and elapsed > 1:
            remaining = (elapsed / iteration) * (self.total - iteration)
            time_info = f"用时: {elapsed:.1f}s | 剩余: {remaining:.1f}s"
        else:
            time_info = f"用时: {elapsed:.1f}s | 剩余: 计算中..."
        
        # 构建进度行
        progress_line = f"\r{self.prefix} |{bar}| {percent}% ({iteration}/{self.total}) | {time_info} | {self.suffix}"
        
        sys.stdout.write(progress_line)
        sys.stdout.flush()
    
    def update(self, iteration, suffix=None):
        """更新进度"""
        if suffix:
            self.suffix = suffix
        self._update(iteration)
    
    def complete(self):
        """完成进度显示"""
        self._update(self.total)
        elapsed = time.time() - self.start_time
        print(f"\n完成! 总用时: {elapsed:.1f}秒")

def format_filename(filename, max_length=20):
    """格式化文件名，确保显示长度合适"""
    if len(filename) <= max_length:
        return filename
    return f"{filename[:max_length//2]}...{filename[-(max_length//2):]}"

def format_size(size_bytes):
    """格式化文件大小显示"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def merge_excel_files(input_folder, output_file, header_rows=2):
    """
    合并多个Excel文件，自动处理前N行重复数据
    
    参数:
    input_folder: 包含Excel文件的文件夹路径
    output_file: 合并后的输出文件路径
    header_rows: 要检查的标题行数(默认为2行)
    """
    # 收集所有Excel文件
    excel_files = [f for f in os.listdir(input_folder) 
                  if f.endswith(('.xlsx', '.xls'))]
    
    if not excel_files:
        print("未找到Excel文件！")
        return
    
    total_files = len(excel_files)
    print(f"发现 {total_files} 个Excel文件，开始处理...")
    print(f"检查前 {header_rows} 行作为标题行")
    print("=" * 80)
    
    # 初始化进度条
    progress = ProgressBar(
        total=total_files,
        prefix="合并进度:",
        suffix="等待开始...",
        length=40
    )
    
    # 存储文件分组信息
    header_groups = {}
    merged_dfs = []
    total_rows_merged = 0
    total_size_processed = 0
    error_count = 0
    
    for i, file in enumerate(excel_files):
        file_path = os.path.join(input_folder, file)
        status = ""
        
        try:
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            total_size_processed += file_size
            
            # 读取前N行数据
            df_header = pd.read_excel(file_path, header=None, nrows=header_rows)
            
            # 生成唯一标识
            header_hash = hashlib.sha256(
                pd.util.hash_pandas_object(df_header).values.tobytes()
            ).hexdigest()
            
            # 检查是否已有相同标题组
            if header_hash in header_groups:
                # 跳过标题行读取数据
                df_data = pd.read_excel(file_path, header=None, skiprows=header_rows)
                status = f"跳过 {header_rows} 行标题 | {len(df_data)}行"
            else:
                # 首次出现此标题组，读取完整数据
                df_data = pd.read_excel(file_path, header=None)
                header_groups[header_hash] = df_header
                status = f"保留完整标题 | {len(df_data)}行"
            
            # 添加到合并列表
            if not df_data.empty:
                merged_dfs.append(df_data)
                total_rows_merged += len(df_data)
                
        except Exception as e:
            error_count += 1
            status = f"错误: {str(e)[:30]}..." if len(str(e)) > 30 else f"错误: {str(e)}"
        
        # 更新进度条
        file_display = format_filename(file)
        size_display = format_size(file_size)
        progress_suffix = f"{file_display} | {size_display} | {status}"
        progress.update(i+1, suffix=progress_suffix)
    
    # 完成文件处理
    progress.complete()
    print("\n" + "=" * 80)
    print(f"文件处理完成! 共处理 {total_files} 个文件")
    print(f"总数据量: {format_size(total_size_processed)}")
    print(f"错误文件数: {error_count}")
    
    # 合并所有数据
    if not merged_dfs:
        print("\n没有有效数据可合并！")
        return
    
    print("\n开始合并数据...")
    merge_start = time.time()
    merged_df = pd.concat(merged_dfs, ignore_index=True)
    merge_time = time.time() - merge_start
    print(f"数据合并完成! 用时 {merge_time:.1f}秒, 总行数: {total_rows_merged}")
    
    # 保存结果
    print("正在保存结果文件...")
    save_start = time.time()
    try:
        merged_df.to_excel(output_file, index=False, header=False)
        save_time = time.time() - save_start
        output_size = format_size(os.path.getsize(output_file))
        
        print("\n" + "=" * 80)
        print(f"合并完成! 成功处理文件: {total_files - error_count}/{total_files}")
        print(f"合并后总行数: {len(merged_df)}")
        print(f"输出文件大小: {output_size}")
        print(f"总处理时间: {time.time() - progress.start_time:.1f}秒")
        print(f"结果已保存至: {output_file}")
        print("=" * 80)
    except Exception as e:
        print(f"\n保存合并文件失败: {e}")

# 使用示例
if __name__ == "__main__":
    # 配置参数
    input_folder = "C:\Users\Administrator\Desktop\123\九江银行.xlsx"  # Excel文件夹路径
    output_file = "C:\Users\Administrator\Desktop\123\九江银行_合并.xlsx"        # 输出文件名
    check_rows = 2                             # 检查的行数(可修改)
    
    # 执行合并
    merge_excel_files(input_folder, output_file, header_rows=check_rows)