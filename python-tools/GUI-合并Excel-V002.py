import pandas as pd
import os
from pathlib import Path
import warnings
import logging
import time
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from threading import Thread

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='excel_merge.log',
    filemode='w'
)

# 忽略openpyxl的样式警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl.styles.stylesheet')
pd.options.mode.chained_assignment = None  # 禁用SettingWithCopyWarning

class ExcelMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel文件合并工具")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 创建主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建输入部分
        self.create_input_section()
        
        # 创建进度和日志部分
        self.create_progress_log_section()
        
        # 初始化变量
        self.input_folder = ""
        self.output_file = ""
        self.file_extension = ".xlsx"
        self.max_header_rows = 5  # 最大检查行数
        self.min_similarity = 0.8  # 相似度阈值
        
    def create_input_section(self):
        """创建输入参数区域"""
        input_frame = ttk.LabelFrame(self.main_frame, text="合并参数设置")
        input_frame.pack(fill=tk.X, padx=5, pady=5, ipadx=10, ipady=10)
        
        # 输入文件夹选择
        folder_frame = ttk.Frame(input_frame)
        folder_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(folder_frame, text="输入文件夹:").pack(side=tk.LEFT, padx=(0, 5))
        self.folder_entry = ttk.Entry(folder_frame, width=50)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(folder_frame, text="浏览...", command=self.browse_folder).pack(side=tk.LEFT)
        
        # 输出文件选择
        output_frame = ttk.Frame(input_frame)
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(output_frame, text="输出文件:").pack(side=tk.LEFT, padx=(0, 5))
        self.output_entry = ttk.Entry(output_frame, width=50)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(output_frame, text="浏览...", command=self.browse_output).pack(side=tk.LEFT)
        
        # 文件扩展名选择
        ext_frame = ttk.Frame(input_frame)
        ext_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(ext_frame, text="文件类型:").pack(side=tk.LEFT, padx=(0, 5))
        self.ext_var = tk.StringVar(value=".xlsx")
        ttk.Radiobutton(ext_frame, text="Excel (.xlsx)", variable=self.ext_var, value=".xlsx").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(ext_frame, text="Excel 97-2003 (.xls)", variable=self.ext_var, value=".xls").pack(side=tk.LEFT)
        
        # 高级设置
        adv_frame = ttk.LabelFrame(input_frame, text="高级设置")
        adv_frame.pack(fill=tk.X, padx=5, pady=5, ipadx=5, ipady=5)
        
        # 最大标题行数
        max_header_frame = ttk.Frame(adv_frame)
        max_header_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(max_header_frame, text="最大标题行检查数:").pack(side=tk.LEFT, padx=(0, 5))
        self.max_header_spin = ttk.Spinbox(max_header_frame, from_=1, to=10, width=5)
        self.max_header_spin.set(5)
        self.max_header_spin.pack(side=tk.LEFT)
        
        # 相似度阈值
        similarity_frame = ttk.Frame(adv_frame)
        similarity_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(similarity_frame, text="标题行相似度阈值:").pack(side=tk.LEFT, padx=(0, 5))
        self.similarity_scale = ttk.Scale(similarity_frame, from_=0.5, to=1.0, value=0.8)
        self.similarity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.similarity_var = tk.StringVar(value="0.80")
        ttk.Label(similarity_frame, textvariable=self.similarity_var, width=4).pack(side=tk.LEFT)
        self.similarity_scale.config(command=lambda v: self.similarity_var.set(f"{float(v):.2f}"))
        
        # 添加来源信息
        self.add_source_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(adv_frame, text="添加来源信息列", variable=self.add_source_var).pack(anchor=tk.W, padx=5, pady=2)
        
        # 合并按钮
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Button(button_frame, text="开始合并", command=self.start_merge).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="退出", command=self.root.destroy).pack(side=tk.LEFT)
    
    def create_progress_log_section(self):
        """创建进度和日志区域"""
        progress_frame = ttk.LabelFrame(self.main_frame, text="合并进度")
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, ipadx=10, ipady=10)
        
        # 进度条
        self.progress_label = ttk.Label(progress_frame, text="准备就绪")
        self.progress_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        # 日志区域
        log_frame = ttk.LabelFrame(progress_frame, text="处理日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def browse_folder(self):
        """选择输入文件夹"""
        folder = filedialog.askdirectory(title="选择Excel文件所在文件夹")
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
    
    def browse_output(self):
        """选择输出文件"""
        file = filedialog.asksaveasfilename(
            title="保存合并结果",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        if file:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, file)
    
    def log_message(self, message):
        """在日志区域添加消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def update_progress(self, value, max_value=None, message=None):
        """更新进度条"""
        if max_value is not None:
            self.progress_bar.config(maximum=max_value)
        
        if value is not None:
            self.progress_bar.config(value=value)
        
        if message:
            self.progress_label.config(text=message)
        
        self.root.update_idletasks()
    
    def start_merge(self):
        """开始合并过程"""
        self.input_folder = self.folder_entry.get()
        self.output_file = self.output_entry.get()
        self.file_extension = self.ext_var.get()
        self.max_header_rows = int(self.max_header_spin.get())
        self.min_similarity = float(self.similarity_var.get())
        
        # 验证输入
        if not self.input_folder or not os.path.isdir(self.input_folder):
            messagebox.showerror("错误", "请选择有效的输入文件夹")
            return
        
        if not self.output_file:
            messagebox.showerror("错误", "请指定输出文件")
            return
        
        # 清空日志
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 在后台线程中运行合并
        self.log_message("开始合并过程...")
        self.update_progress(0, 100, "准备中...")
        Thread(target=self.merge_excel_files, daemon=True).start()
    
    def detect_data_start_row(self, df):
        """
        自动检测数据开始的行索引
        通过比较连续行的相似度来确定标题行结束的位置
        """
        # 如果数据框行数小于2，直接返回0
        if len(df) < 2:
            return 0
        
        # 只检查前max_header_rows行
        check_rows = min(self.max_header_rows, len(df))
        
        # 如果只有一行，直接返回0
        if check_rows == 1:
            return 0
        
        # 计算行之间的相似度
        similarities = []
        for i in range(check_rows - 1):
            # 比较连续两行
            row1 = df.iloc[i].astype(str).values
            row2 = df.iloc[i+1].astype(str).values
            
            # 计算相似度 - 修复语法错误
            same_count = sum(1 for a, b in zip(row1, row2) if a == b)
            similarity = same_count / len(row1) if len(row1) > 0 else 0
            
            similarities.append(similarity)
            
            # 如果相似度低于阈值，说明数据开始了
            if similarity < self.min_similarity:
                return i + 1  # 数据从下一行开始
        
        # 如果所有检查的行都相似，返回检查行数的下一行
        return check_rows if check_rows < len(df) else 0
    
    def merge_excel_files(self):
        """合并Excel文件的主函数"""
        start_time = time.time()
        all_data = []
        processed_files = []
        error_files = []
        total_sheets = 0
        total_rows = 0
        skipped_files = []
        
        try:
            # 获取文件列表
            file_paths = list(Path(self.input_folder).glob(f"*{self.file_extension}"))
            
            if not file_paths:
                self.log_message(f"错误: 在 {self.input_folder} 中未找到 {self.file_extension} 文件")
                return
            
            self.log_message(f"发现 {len(file_paths)} 个Excel文件待处理...")
            
            # 更新进度条最大值
            self.update_progress(0, len(file_paths), "开始处理文件...")
            
            # 处理每个文件
            for idx, file_path in enumerate(file_paths):
                try:
                    # 更新进度
                    self.update_progress(idx + 1, message=f"处理文件: {file_path.name} ({idx+1}/{len(file_paths)})")
                    
                    # 读取Excel文件（包含所有工作表）
                    engine = 'openpyxl' if self.file_extension == '.xlsx' else 'xlrd'
                    excel_file = pd.read_excel(file_path, sheet_name=None, engine=engine)
                    
                    file_sheets = 0
                    file_rows = 0
                    
                    # 遍历文件中的每个工作表
                    for sheet_name, df in excel_file.items():
                        # 跳过空工作表
                        if df.empty:
                            self.log_message(f"  工作表 '{sheet_name}' 为空 - 跳过")
                            continue
                        
                        # 自动检测数据开始行
                        start_row = self.detect_data_start_row(df.head(self.max_header_rows + 1))
                        
                        # 如果检测到标题行
                        if start_row > 0:
                            # 保留原始列名
                            original_columns = df.columns.tolist()
                            
                            # 从检测到的行开始读取数据
                            data_df = df.iloc[start_row:].copy()
                            
                            # 重置列名为原始列名
                            data_df.columns = original_columns
                            
                            # 添加来源标记
                            if self.add_source_var.get():
                                data_df.insert(0, '来源文件', file_path.name)
                                data_df.insert(1, '来源工作表', sheet_name)
                            
                            # 添加到合并列表
                            all_data.append(data_df)
                            total_sheets += 1
                            total_rows += len(data_df)
                            file_sheets += 1
                            file_rows += len(data_df)
                            
                            self.log_message(f"  工作表 '{sheet_name}': 跳过前 {start_row} 行标题，读取 {len(data_df)} 行数据")
                        else:
                            # 没有检测到重复标题，使用整个工作表
                            if self.add_source_var.get():
                                df.insert(0, '来源文件', file_path.name)
                                df.insert(1, '来源工作表', sheet_name)
                            
                            all_data.append(df)
                            total_sheets += 1
                            total_rows += len(df)
                            file_sheets += 1
                            file_rows += len(df)
                            
                            self.log_message(f"  工作表 '{sheet_name}': 未检测到重复标题，读取 {len(df)} 行数据")
                    
                    if file_sheets > 0:
                        processed_files.append(file_path.name)
                        self.log_message(f"✓ 成功处理: {file_path.name} (包含 {file_sheets} 个工作表，{file_rows} 行数据)\n")
                    else:
                        skipped_files.append(file_path.name)
                        self.log_message(f"⚠ 跳过: {file_path.name} (没有有效工作表)\n")
                    
                except Exception as e:
                    error_msg = f"处理文件 {file_path.name} 时出错: {str(e)}"
                    self.log_message(f"✗ {error_msg}")
                    logging.error(error_msg, exc_info=True)
                    error_files.append(file_path.name)
            
            if not all_data:
                self.log_message("错误: 所有文件处理失败，未找到可合并的数据")
                return
            
            # 合并所有数据
            self.update_progress(None, message="合并数据中...")
            self.log_message("\n合并数据中...")
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # 保存结果
            self.update_progress(None, message="保存合并文件...")
            self.log_message(f"保存合并结果到: {self.output_file}")
            combined_df.to_excel(self.output_file, index=False, engine='openpyxl')
            
            # 性能统计
            processing_time = time.time() - start_time
            mins, secs = divmod(processing_time, 60)
            
            # 输出摘要
            summary = f"""
            ====== 合并完成 ======
            总处理文件数: {len(file_paths)}
            成功处理文件: {len(processed_files)}
            跳过文件: {len(skipped_files)}
            失败文件: {len(error_files)}
            合并工作表总数: {total_sheets}
            总行数: {total_rows}
            输出文件: {self.output_file}
            处理时间: {int(mins)}分{secs:.1f}秒
            """
            
            self.log_message(summary)
            self.update_progress(100, message="合并完成!")
            messagebox.showinfo("完成", f"Excel文件合并完成!\n总处理文件: {len(file_paths)}\n合并工作表: {total_sheets}\n总行数: {total_rows}")
            
        except Exception as e:
            error_msg = f"合并过程中发生错误: {str(e)}"
            self.log_message(f"✗ {error_msg}")
            logging.error(error_msg, exc_info=True)
            messagebox.showerror("错误", error_msg)
            self.update_progress(0, message="合并失败")

# 运行应用程序
if __name__ == "__main__":
    root = tk.Tk()
    app = ExcelMergerApp(root)
    root.mainloop()