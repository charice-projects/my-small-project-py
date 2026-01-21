"""#########################################
            【企查查数据去重】
--------------------------------------------
功能：
    1、以电话号码和公司名为依据，数据去重
    2、将"有效手机号"和"更多电话"合并到"所有号码"列
    3、保存的电话号码，以空格+换行保存
    4、将公司名字不同但电话号码相同的数据行移动到一起
------------------------------------------
使用说明：
    1. 运行脚本后，按照提示输入输入文件和输出文件的路径
    2. 确保输入文件包含"企业名称"、"有效手机号"和"更多电话"列
    3. 处理结果将保存到指定的输出文件
------------------------------------------
运行环境： win7+， python3.8
------------------------------------------
创建日期：2025年8月1日  |   创建人：西施先生
修改日期：2025年8月2日  |   修改人：西施先生
------------------------------------------
"""########################################

import pandas as pd
import re
import numpy as np
from collections import defaultdict
from tqdm import tqdm
import time
import os

def extract_phone_numbers(phone_str):
    """
    从字符串中提取所有11位手机号码，忽略各种分隔符
    返回排序后的唯一号码列表
    
    参数:
        phone_str: 包含电话号码的字符串
        
    返回:
        排序后的唯一手机号码列表
    """
    if pd.isna(phone_str) or phone_str == "":
        return []
    
    # 统一替换所有可能的分隔符为逗号
    phone_str = re.sub(r'[，；；\s、/|\\-]', ',', str(phone_str))
    # 提取所有11位手机号
    phones = re.findall(r'1[3-9]\d{9}', phone_str)
    # 去重并排序
    return sorted(set(phones))

def group_by_phone_numbers(df):
    """
    将公司名字不同但电话号码相同的数据行移动到一起
    
    参数:
        df: 包含电话号码的DataFrame
        
    返回:
        重新排列后的DataFrame
    """
    # 创建一个字典来记录电话号码对应的行索引
    phone_to_indices = defaultdict(list)
    
    # 遍历每一行，记录电话号码对应的索引
    for idx, phones in enumerate(df["所有号码"]):
        if phones:  # 如果有电话号码
            for phone in phones:
                phone_to_indices[phone].append(idx)
    
    # 找出有共享电话号码的行组
    shared_phone_groups = []
    used_indices = set()
    
    for phone, indices in phone_to_indices.items():
        if len(indices) > 1:  # 这个电话号码被多行使用
            group_indices = [idx for idx in indices if idx not in used_indices]
            if group_indices:
                shared_phone_groups.append(group_indices)
                used_indices.update(group_indices)
    
    # 如果没有共享电话号码的行，直接返回原数据框
    if not shared_phone_groups:
        return df
    
    # 创建一个新顺序：先是没有共享电话号码的行，然后是共享电话号码的组
    new_order = []
    
    # 添加没有共享电话号码的行
    for idx in range(len(df)):
        if idx not in used_indices:
            new_order.append(idx)
    
    # 添加共享电话号码的组
    for group in shared_phone_groups:
        new_order.extend(group)
    
    # 按照新顺序重新排列数据框
    return df.iloc[new_order].reset_index(drop=True)

def get_file_path(prompt, default_path=""):
    """
    获取用户输入的文件路径，支持拖拽文件到命令行
    
    参数:
        prompt: 提示信息
        default_path: 默认路径（可选）
        
    返回:
        用户输入的文件路径
    """
    print(prompt)
    if default_path:
        print(f"默认路径: {default_path} (直接回车使用默认路径)")
    
    while True:
        path = input("请输入文件路径(或拖拽文件到此处): ").strip().strip('"')
        
        # 如果用户直接回车且提供了默认路径，则使用默认路径
        if not path and default_path:
            return default_path
        
        # 检查路径是否存在
        if not os.path.exists(path):
            print(f"错误: 文件不存在 - {path}")
            print("请重新输入有效的文件路径")
            continue
        
        return path

def main():
    # 显示欢迎信息
    print("=" * 60)
    print("企查查数据去重工具")
    print("=" * 60)
    
    # 获取输入文件路径
    input_file = get_file_path("请选择输入Excel文件:")
    
    # 获取输出文件路径
    default_output = os.path.join(
        os.path.dirname(input_file), 
        f"{os.path.splitext(os.path.basename(input_file))[0]}_去重版.xlsx"
    )
    output_file = get_file_path("请指定输出Excel文件:", default_output)
    
    print("=" * 60)
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print("=" * 60)
    
    # 初始化进度条
    pbar = tqdm(total=100, desc="准备处理", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
    
    try:
        # 更新进度条状态
        pbar.set_description("📂 读取Excel文件")
        df = pd.read_excel(input_file)
        total_rows = len(df)
        pbar.update(10)
        pbar.set_postfix(rows=f"{total_rows:,}条")
        
        # 检查必要的列是否存在
        required_columns = ["企业名称", "有效手机号", "更多电话"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            pbar.close()
            print(f"✗ 错误: 缺少必要列 - {', '.join(missing_cols)}")
            print("请确保输入文件包含这些列")
            return
        
        # 处理电话号码 - 有效手机号
        pbar.set_description("📱 处理有效手机号")
        df["有效手机号_清洗"] = df["有效手机号"].apply(extract_phone_numbers)
        pbar.update(15)
        
        # 处理电话号码 - 更多电话
        pbar.set_description("📞 处理更多电话")
        df["更多电话_清洗"] = df["更多电话"].apply(extract_phone_numbers)
        pbar.update(15)
        
        # 合并所有电话号码
        pbar.set_description("🔀 合并电话号码")
        df["所有号码"] = df.apply(
            lambda row: sorted(set(row["有效手机号_清洗"] + row["更多电话_清洗"])), 
            axis=1
        )
        pbar.update(15)
        
        # 创建去重标识
        pbar.set_description("🏷️ 创建去重标识")
        df["去重标识"] = df.apply(
            lambda row: (row["企业名称"], tuple(sorted(row["所有号码"]))), 
            axis=1
        )
        pbar.update(15)
        
        # 去重处理
        pbar.set_description("🧹 执行去重操作")
        dedup_df = df.drop_duplicates(subset=["去重标识"], keep="first")
        dedup_count = len(dedup_df)
        removed_count = total_rows - dedup_count
        pbar.update(10)
        pbar.set_postfix(rows=f"{total_rows:,}→{dedup_count:,}", removed=f"{removed_count:,}")
        
        # 新增功能：将公司名字不同但电话号码相同的数据行移动到一起
        pbar.set_description("📊 按电话号码分组排列")
        dedup_df = group_by_phone_numbers(dedup_df)
        pbar.update(5)
        
        # 创建"所有号码"列（用空格+换行分隔号码）
        pbar.set_description("📋 格式化电话号码")
        dedup_df["所有号码"] = dedup_df["所有号码"].apply(
            lambda phones: " \n".join(phones) if phones else ""
        )
        pbar.update(5)
        
        # 删除中间列
        dedup_df = dedup_df.drop(columns=[
            "有效手机号", "更多电话", "有效手机号_清洗", 
            "更多电话_清洗", "去重标识"
        ])
        
        # 调整列顺序
        cols = dedup_df.columns.tolist()
        name_idx = cols.index("企业名称")
        new_cols = cols[:name_idx+1] + ["所有号码"] + [
            col for col in cols[name_idx+1:] if col != "所有号码"
        ]
        
        # 保存结果
        pbar.set_description("💾 保存结果文件")
        dedup_df[new_cols].to_excel(output_file, index=False)
        pbar.update(10)
        
        # 完成处理
        pbar.set_description("✅ 处理完成")
        pbar.close()
        
        # 显示统计信息
        print("\n" + "=" * 60)
        print(f"处理完成: {os.path.basename(input_file)} → {os.path.basename(output_file)}")
        print(f"原始记录数: {total_rows:,}")
        print(f"去重后记录数: {dedup_count:,}")
        print(f"删除重复记录: {removed_count:,} 条 ({removed_count/total_rows:.2%})")
        print("=" * 60)
        
    except Exception as e:
        pbar.set_description("❌ 处理出错")
        pbar.close()
        print(f"\n✗ 处理过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 显示使用说明
    print("企查查数据去重工具 - 使用说明")
    print("1. 请确保输入文件包含'企业名称'、'有效手机号'和'更多电话'列")
    print("2. 您可以输入文件路径或直接将文件拖拽到命令行窗口")
    print("3. 处理结果将保存到您指定的输出文件")
    print("-" * 60)
    
    # 确认是否继续
    response = input("是否继续执行? (y/n): ")
    if response.lower() in ['y', 'yes', '是']:
        main()
    else:
        print("操作已取消")