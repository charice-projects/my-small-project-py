"""
Excel转vCard模块
====================================
[模块信息]
    模块名称: ExcelToVCFConverter
    版本号: 1.0.0
    发布日期: 2025-11-13
    维护团队: 西施先生
    
[库信息]    
    pip install openpyxl
    pip install pandas

[功能概述]
    本模块专门用于将Excel数据转换为标准vCard格式，
    便于将联系人批量导入个人手机设备。

[适用场景]
    - 电脑客户转移至手机通讯里
    - 客户通讯录同步


[安全说明]
    - 本工具仅在本地运行，数据不会上传至任何服务器
    - 建议在处理敏感联系人信息时确保环境安全

[技术支持]
    如有技术问题，请联系王牌队史熙
    电话:  | 邮箱: 

[更新日志]
    v1.0.0 - 初始发布版本 2025年11月13日

"""




import pandas as pd
import re
import os

class ExcelToVCFConverter:
    def __init__(self):
        # 字段映射配置
        self.field_mapping = {
            'name': ['姓名', '名字', '名称', 'name', '联系人', '全名'],
            'mobile': ['手机','号码', '移动电话', '手机号', 'mobile', '电话', '联系电话', '手机号码', '电话1'],
            'tel_work': ['工作电话', '办公电话', '公司电话', 'work phone', '电话2'],
            'tel_home': ['家庭电话', '住宅电话', 'home phone', '电话3'],
            'company': ['公司', '单位', 'company', '组织', '机构'],
            'title': ['职位', '职务', 'title', 'position'],
            'note': ['备注', '说明', 'note', '注释', '描述'],
            'email': ['邮箱', '电子邮件', 'email', '电子邮箱'],
            'address': ['地址', '住址', 'address']
        }
    
    def clean_text(self, text):
        """清理文本，移除vCard中不允许的特殊字符"""
        if pd.isna(text) or text == '':
            return ""
        
        text_str = str(text).strip()
        # 移除可能导致vCard解析问题的字符
        cleaned = re.sub(r'[\n\r]', ' ', text_str)  # 换行符替换为空格
        return cleaned
    
    def clean_phone(self, phone):
        """清理电话号码"""
        if pd.isna(phone) or phone == '':
            return ""
        
        phone_str = str(phone).strip()
        # 保留数字、空格、+号和括号
        cleaned = re.sub(r'[^\d+\s\(\)\-]', '', phone_str)
        return cleaned
    
    def detect_columns(self, df):
        """检测Excel中的列名并映射到vCard字段"""
        column_mapping = {}
        
        for col in df.columns:
            col_str = str(col).strip()
            col_lower = col_str.lower()
            matched = False
            
            for field, keywords in self.field_mapping.items():
                for keyword in keywords:
                    if keyword.lower() in col_lower:
                        column_mapping[col] = field
                        matched = True
                        print(f"  映射: '{col}' -> {field}")
                        break
                if matched:
                    break
            
            if not matched:
                column_mapping[col] = col
                print(f"  未识别: '{col}'，将保留原值")
        
        return column_mapping
    
    def create_vcard(self, row, column_mapping):
        """创建简洁格式的vCard"""
        vcard_lines = [
            "BEGIN:VCARD",
            "VERSION:3.0"
        ]
        
        # 处理姓名（必需字段）
        name = ""
        for col, field in column_mapping.items():
            if field == 'name' and pd.notna(row[col]) and str(row[col]).strip():
                name = self.clean_text(row[col])
                break
        
        # 如果没有找到姓名，使用第一个非空字段
        if not name:
            for col in row.index:
                if pd.notna(row[col]) and str(row[col]).strip():
                    name = self.clean_text(row[col])
                    break
        
        # 确保有姓名
        if not name:
            name = "未知联系人"
        
        # 添加姓名字段
        vcard_lines.append(f"N:{name}")
        vcard_lines.append(f"FN:{name}")
        
        # 处理电话号码
        phones = []
        for col, field in column_mapping.items():
            if field in ['mobile', 'tel_work', 'tel_home'] and pd.notna(row[col]) and str(row[col]).strip():
                phone = self.clean_phone(row[col])
                if phone:
                    phones.append((field, phone))
        
        # 添加电话，移动电话优先
        mobile_added = False
        work_added = False
        home_added = False
        
        for field, phone in phones:
            if field == 'mobile' and not mobile_added:
                vcard_lines.append(f"TEL;CELL:{phone}")
                mobile_added = True
            elif field == 'tel_work' and not work_added:
                vcard_lines.append(f"TEL;WORK:{phone}")
                work_added = True
            elif field == 'tel_home' and not home_added:
                vcard_lines.append(f"TEL;HOME:{phone}")
                home_added = True
        
        # 如果没有移动电话但有其他电话，添加第一个作为主要电话
        if not mobile_added and phones:
            vcard_lines.append(f"TEL;CELL:{phones[0][1]}")
        
        # 处理公司
        company = ""
        for col, field in column_mapping.items():
            if field == 'company' and pd.notna(row[col]) and str(row[col]).strip():
                company = self.clean_text(row[col])
                break
        
        if company:
            vcard_lines.append(f"ORG:{company}")
        
        # 处理职位
        title = ""
        for col, field in column_mapping.items():
            if field == 'title' and pd.notna(row[col]) and str(row[col]).strip():
                title = self.clean_text(row[col])
                break
        
        if title:
            vcard_lines.append(f"TITLE:{title}")
        
        # 处理备注
        note = ""
        for col, field in column_mapping.items():
            if field == 'note' and pd.notna(row[col]) and str(row[col]).strip():
                note = self.clean_text(row[col])
                break
        
        if note:
            vcard_lines.append(f"NOTE:{note}")
        
        # 处理邮箱
        email = ""
        for col, field in column_mapping.items():
            if field == 'email' and pd.notna(row[col]) and str(row[col]).strip():
                email = self.clean_text(row[col])
                break
        
        if email and '@' in email:
            vcard_lines.append(f"EMAIL:{email}")
        
        # 处理地址
        address = ""
        for col, field in column_mapping.items():
            if field == 'address' and pd.notna(row[col]) and str(row[col]).strip():
                address = self.clean_text(row[col])
                break
        
        if address:
            vcard_lines.append(f"ADR:;;{address};;;;")
        
        vcard_lines.append("END:VCARD")
        return '\n'.join(vcard_lines)
    
    def convert_excel_to_vcf(self, excel_file, vcf_file=None, sheet_name=0):
        """主转换函数"""
        try:
            # 确保Excel文件路径是绝对路径
            excel_file = os.path.abspath(excel_file)
            print(f"正在读取Excel文件: {excel_file}")
            
            # 读取Excel文件
            df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=str)
            df = df.fillna('')
            
            print(f"成功读取Excel文件，共{len(df)}条记录")
            print(f"检测到列: {list(df.columns)}")
            
            # 检测列映射
            print("开始字段映射检测...")
            column_mapping = self.detect_columns(df)
            
            # 生成输出文件名 - 默认保存在原Excel文件同一目录
            if vcf_file is None:
                base_name = os.path.splitext(excel_file)[0]
                vcf_file = f"{base_name}_通讯录.vcf"
            else:
                # 如果用户指定了输出文件，但只给了文件名没有路径，则使用原Excel文件目录
                if os.path.dirname(vcf_file) == "":
                    excel_dir = os.path.dirname(excel_file)
                    vcf_file = os.path.join(excel_dir, vcf_file)
            
            # 确保输出文件扩展名正确
            if not vcf_file.lower().endswith('.vcf'):
                vcf_file += '.vcf'
            
            # 创建vCard内容
            vcards = []
            successful_count = 0
            
            print("开始转换数据...")
            for index, row in df.iterrows():
                try:
                    if (index + 1) % 10 == 0 or (index + 1) == len(df):
                        print(f"  正在处理第 {index+1}/{len(df)} 条记录...")
                    
                    vcard = self.create_vcard(row, column_mapping)
                    vcards.append(vcard)
                    successful_count += 1
                except Exception as e:
                    print(f"  警告: 第{index+1}行数据处理失败 - {str(e)}")
                    continue
            
            # 写入文件 - 使用UTF-8编码
            with open(vcf_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(vcards))
            
            print(f"\n✅ 转换完成!")
            print(f"   成功转换: {successful_count}/{len(df)} 条记录")
            print(f"   输出文件: {vcf_file}")
            print(f"   文件大小: {os.path.getsize(vcf_file)} 字节")
            
            # 显示文件预览
            print("\n📄 文件预览 (前3个联系人):")
            print("-" * 40)
            with open(vcf_file, 'r', encoding='utf-8') as f:
                content = f.read()
                vcard_blocks = content.split('BEGIN:VCARD')
                for i, block in enumerate(vcard_blocks[:4]):  # 前3个加一个空块
                    if block.strip() and i < 3:
                        print(f"联系人 {i+1}:")
                        for line in block.strip().split('\n')[:6]:  # 只显示前6行
                            if line and not line.startswith('END:VCARD'):
                                print(f"  {line}")
                        print()
            
            return vcf_file, successful_count
            
        except FileNotFoundError:
            print(f"❌ 错误: 找不到文件 '{excel_file}'")
            return None, 0
        except PermissionError:
            print(f"❌ 错误: 没有权限访问文件 '{excel_file}'")
            return None, 0
        except Exception as e:
            print(f"❌ 转换过程中出错: {str(e)}")
            return None, 0

def main():
    converter = ExcelToVCFConverter()
    
    print("Excel转vCard通讯录转换器")
    print("=" * 50)
    
    # 输入Excel文件路径
    excel_file = input("请输入Excel文件路径: ").strip().strip('"')
    
    if not os.path.exists(excel_file):
        print("❌ 错误: 文件不存在，请检查路径是否正确")
        return
    
    # 检查文件扩展名
    if not excel_file.lower().endswith(('.xlsx', '.xls')):
        print("❌ 错误: 文件不是Excel格式 (.xlsx 或 .xls)")
        return
    
    # 选择工作表
    sheet_name = 0
    try:
        excel_file_obj = pd.ExcelFile(excel_file)
        sheet_names = excel_file_obj.sheet_names
        if len(sheet_names) > 1:
            print(f"发现多个工作表: {sheet_names}")
            sheet_name = input("请选择要使用的工作表 (直接回车使用第一个): ").strip()
            if not sheet_name:
                sheet_name = sheet_names[0]
            elif sheet_name not in sheet_names:
                print(f"⚠️  警告: 工作表 '{sheet_name}' 不存在，将使用第一个工作表")
                sheet_name = sheet_names[0]
        else:
            sheet_name = sheet_names[0]
        excel_file_obj.close()
    except Exception as e:
        print(f"⚠️  警告: 无法读取工作表信息，将使用默认工作表 - {str(e)}")
    
    # 获取Excel文件所在目录，用于默认保存路径
    excel_dir = os.path.dirname(os.path.abspath(excel_file))
    default_vcf_name = f"{os.path.splitext(os.path.basename(excel_file))[0]}_通讯录.vcf"
    default_vcf_path = os.path.join(excel_dir, default_vcf_name)
    
    # 指定输出文件路径
    output_file = input(f"请输入输出vcf文件路径 (直接回车将保存为: {default_vcf_path}): ").strip().strip('"')
    if not output_file:
        output_file = default_vcf_path
    elif not output_file.lower().endswith('.vcf'):
        output_file += '.vcf'
    
    # 如果用户只输入了文件名，没有路径，则使用原Excel文件目录
    if os.path.dirname(output_file) == "":
        output_file = os.path.join(excel_dir, output_file)
    
    print(f"\n输出文件将保存到: {output_file}")
    
    print("\n开始转换...")
    result_file, count = converter.convert_excel_to_vcf(excel_file, output_file, sheet_name)
    
    if result_file:
        # 打开文件所在目录
        result_dir = os.path.dirname(result_file)
        result_name = os.path.basename(result_file)
        
        print(f"\n📱 导入到手机的方法:")
        print("1. 将vcf文件发送到手机 (通过邮件、微信、QQ等)")
        print("2. 在手机上使用『文件管理』应用找到vcf文件")
        print("3. 点击vcf文件，选择『联系人』或『通讯录』应用打开")
        print("4. 确认导入所有联系人")
        print(f"\n💡 提示:")
        print(f"   - 输出文件: {result_file}")
        print(f"   - 此格式兼容大多数智能手机")
        print(f"   - 如果联系人较多，建议分批次导入")
        print(f"   - 导入前请备份现有联系人")
        
        # 提供打开文件所在目录的选项
        try:
            open_folder = input("\n是否要打开文件所在目录? (y/n, 默认n): ").strip().lower()
            if open_folder == 'y' or open_folder == 'yes':
                if os.name == 'nt':  # Windows
                    os.system(f'explorer /select,"{result_file}"')
                elif os.name == 'posix':  # macOS or Linux
                    if sys.platform == 'darwin':  # macOS
                        os.system(f'open -R "{result_file}"')
                    else:  # Linux
                        os.system(f'xdg-open "{result_dir}"')
                print("已尝试打开文件所在目录")
        except:
            print("无法自动打开文件目录，请手动访问")

def quick_convert(excel_file, vcf_file=None, sheet_name=0):
    """
    快速转换函数
    
    参数:
        excel_file: Excel文件路径
        vcf_file: 输出的vcf文件路径 (可选)
        sheet_name: 工作表名称或索引 (可选)
    
    返回:
        (vcf_file路径, 成功转换的记录数)
    """
    converter = ExcelToVCFConverter()
    return converter.convert_excel_to_vcf(excel_file, vcf_file, sheet_name)

if __name__ == "__main__":
    # 确保导入sys模块用于打开目录
    import sys
    
    main()
    

