"""
vCard转Excel模块
====================================
[模块信息]
    模块名称: VCFToExcelConverter
    版本号: 1.0.0
    发布日期: 2025-11-13
    维护团队: 西施先生
    
[库信息]    
    pip install pandas
    pip install openpyxl

[功能概述]
    本模块专门用于将vCard(.vcf)文件转换为Excel格式，
    支持解析多种vCF格式，包括vCard 2.1, 3.0, 4.0等。

[适用场景]
    - 从手机导出的通讯录转为Excel表格
    - 不同设备间联系人格式转换
    - 联系人数据备份与分析

[支持的vCF格式]
    - vCard 2.1 (主要来自旧设备)
    - vCard 3.0 (标准格式)
    - vCard 4.0 (较新格式)
    - 多种编码格式 (UTF-8, GBK, ANSI等)
    - 折叠行格式处理
    - 多值字段处理

[安全说明]
    - 本工具仅在本地运行，数据不会上传至任何服务器
    - 建议在处理敏感联系人信息时确保环境安全

[技术支持]
    如有技术问题，请联系王牌队史熙
    电话: 17807075693 | 邮箱: 930273578@qq.com

[更新日志]
    v1.0.0 - 初始发布版本     2025年11月13日
    v2.0.0 - 增强版          2026年01月26日
    
-------------------------------------------------
    
[核心功能]
    1. 精确识别手机号与其他电话号码
    2. 完整提取备注、公司、邮箱、分组等信息
    3. 支持多种vCard版本和编码格式
    4. 智能处理多值字段
    5. 提供详细的数据统计和预览

[支持的字段]
    ✅ 基础信息: 姓名、姓氏、名字
    ✅ 联系方式: 手机、工作电话、家庭电话、其他电话
    ✅ 职业信息: 公司、部门、职位
    ✅ 联系信息: 邮箱、网址、地址
    ✅ 个人资料: 生日、备注、分组、分类
    ✅ 扩展字段: 所有非标准字段（自动识别）
  
  
[依赖库]
    pip install pandas openpyxl chardet

"""

import pandas as pd
import re
import os
import sys
import base64
import quopri
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
import chardet
from datetime import datetime
import unicodedata
from collections import defaultdict

@dataclass
class Contact:
    """联系人数据类 - 完整字段支持"""
    # 基础信息
    full_name: str = ""
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    prefix: str = ""
    suffix: str = ""
    
    # 联系电话
    mobile: List[str] = field(default_factory=list)
    tel_work: List[str] = field(default_factory=list)
    tel_home: List[str] = field(default_factory=list)
    tel_other: List[str] = field(default_factory=list)
    fax: List[str] = field(default_factory=list)
    
    # 职业信息
    company: str = ""
    department: str = ""
    title: str = ""
    
    # 联系信息
    emails: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    
    # 地址信息
    address_home: Dict[str, str] = field(default_factory=dict)
    address_work: Dict[str, str] = field(default_factory=dict)
    address_other: Dict[str, str] = field(default_factory=dict)
    
    # 个人资料
    birthday: str = ""
    anniversary: str = ""
    note: str = ""
    categories: List[str] = field(default_factory=list)
    nickname: str = ""
    gender: str = ""
    
    # 其他字段
    photo: str = ""
    version: str = ""
    uid: str = ""
    
    # 扩展字段
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def add_phone(self, phone_type: str, number: str):
        """添加电话号码到对应列表"""
        number = self.clean_phone_number(number)
        if not number:
            return
            
        phone_type = phone_type.upper()
        
        if 'CELL' in phone_type or 'MOBILE' in phone_type:
            self.mobile.append(number)
        elif 'WORK' in phone_type:
            self.tel_work.append(number)
        elif 'HOME' in phone_type:
            self.tel_home.append(number)
        elif 'FAX' in phone_type:
            self.fax.append(number)
        else:
            self.tel_other.append(number)
    
    def clean_phone_number(self, phone: str) -> str:
        """清理电话号码"""
        if not phone or not isinstance(phone, str):
            return ""
        
        # 保留数字、+号、空格、括号
        cleaned = re.sub(r'[^\d+\s\(\)\-]', '', phone.strip())
        
        # 如果是11位数字，格式化为 3-4-4 格式
        if len(cleaned) == 11 and cleaned.startswith(('13', '14', '15', '16', '17', '18', '19')):
            return f"{cleaned[:3]} {cleaned[3:7]} {cleaned[7:]}"
        
        return cleaned
    
    def get_primary_mobile(self) -> str:
        """获取主要手机号码"""
        return self.mobile[0] if self.mobile else ""
    
    def get_all_phones_formatted(self) -> str:
        """获取所有电话的格式化字符串"""
        phones = []
        if self.mobile:
            phones.append(f"手机: {', '.join(self.mobile)}")
        if self.tel_work:
            phones.append(f"工作: {', '.join(self.tel_work)}")
        if self.tel_home:
            phones.append(f"家庭: {', '.join(self.tel_home)}")
        if self.tel_other:
            phones.append(f"其他: {', '.join(self.tel_other)}")
        if self.fax:
            phones.append(f"传真: {', '.join(self.fax)}")
        return "; ".join(phones)


class VCFToExcelConverter:
    def __init__(self, encoding: str = 'auto', decode_qp: bool = True):
        """
        初始化转换器
        
        参数:
            encoding: 文件编码
            decode_qp: 是否解码Quoted-Printable编码
        """
        self.encoding = encoding
        self.decode_qp = decode_qp  # 重命名以避免命名冲突
        self.contacts: List[Contact] = []
        self.field_stats = defaultdict(int)
        self.encoding_stats = defaultdict(int)
        
        # 常见字段映射
        self.field_mapping = {
            'FN': 'full_name',
            'N': 'name_structured',
            'TEL': 'phone',
            'EMAIL': 'email',
            'ORG': 'organization',
            'TITLE': 'title',
            'ADR': 'address',
            'NOTE': 'note',
            'BDAY': 'birthday',
            'URL': 'url',
            'PHOTO': 'photo',
            'CATEGORIES': 'categories',
            'NICKNAME': 'nickname',
            'GENDER': 'gender',
            'UID': 'uid',
            'X-ANNIVERSARY': 'anniversary',
            'X-DEPARTMENT': 'department',
        }
    
    def detect_encoding(self, file_path: str) -> str:
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(50000)
                if not raw_data:
                    return 'utf-8'
                
                result = chardet.detect(raw_data)
                if result['encoding'] and result['confidence'] > 0.7:
                    return result['encoding']
                
            # 尝试常见编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'iso-8859-1']
            for enc in encodings:
                try:
                    raw_data.decode(enc)
                    return enc
                except:
                    continue
        except Exception as e:
            print(f"编码检测失败: {e}")
        
        return 'utf-8'
    
    def decode_quoted_printable_text(self, text: str, charset: str = 'UTF-8') -> str:
        """解码Quoted-Printable编码"""
        try:
            # 处理 =E5=88=98 格式
            decoded = quopri.decodestring(text.replace('=\n', '').replace('=\r\n', '').encode('latin-1'))
            
            # 尝试多种编码
            for enc in [charset.lower(), 'utf-8', 'gbk', 'gb2312', 'iso-8859-1']:
                try:
                    return decoded.decode(enc)
                except:
                    continue
            
            return decoded.decode('utf-8', errors='replace')
        except Exception as e:
            print(f"Quoted-Printable解码失败: {e}")
            return text
    
    def parse_field(self, line: str) -> Tuple[str, Dict[str, str], str]:
        """解析字段行，返回(字段名, 参数字典, 字段值)"""
        if ':' not in line:
            return '', {}, ''
        
        # 分割字段名和值
        field_part, value_part = line.split(':', 1)
        field_name = field_part.split(';')[0].upper()
        
        # 解析参数
        params = {}
        for part in field_part.split(';')[1:]:
            if '=' in part:
                key, val = part.split('=', 1)
                params[key.upper()] = val
            else:
                # 对于像 TEL;CELL 这样的简单类型
                params['TYPE'] = part
        
        # 处理编码
        value = value_part.strip()
        
        if 'ENCODING' in params:
            encoding = params['ENCODING'].upper()
            charset = params.get('CHARSET', 'UTF-8')
            
            if encoding == 'QUOTED-PRINTABLE' and self.decode_qp:
                value = self.decode_quoted_printable_text(value, charset)
                self.encoding_stats['quoted_printable'] += 1
            elif encoding in ['BASE64', 'B']:
                try:
                    value = base64.b64decode(value).decode(charset, errors='replace')
                    self.encoding_stats['base64'] += 1
                except:
                    pass
        
        return field_name, params, value
    
    def read_vcf_file(self, file_path: str) -> List[str]:
        """读取VCF文件并处理编码"""
        # 检测编码
        encoding_to_use = self.encoding
        if encoding_to_use == 'auto':
            encoding_to_use = self.detect_encoding(file_path)
            print(f"检测到编码: {encoding_to_use}")
        
        # 尝试读取文件
        encodings_to_try = [encoding_to_use, 'utf-8', 'gbk', 'gb2312', 'latin-1', 'iso-8859-1']
        
        for enc in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=enc, errors='replace') as f:
                    content = f.read()
                print(f"成功使用 {enc} 编码读取文件")
                self.encoding = enc
                return content.splitlines()
            except Exception as e:
                print(f"使用 {enc} 编码读取失败: {e}")
                continue
        
        # 如果所有编码都失败，尝试二进制读取
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            # 尝试用utf-8解码并忽略错误
            return content.decode('utf-8', errors='ignore').splitlines()
        except Exception as e:
            raise Exception(f"无法读取文件: {e}")
    
    def unfold_lines(self, lines: List[str]) -> List[str]:
        """处理折叠行"""
        unfolded = []
        buffer = ""
        
        for line in lines:
            line = line.rstrip('\r\n')
            
            # 如果行以空格或制表符开头，说明是上一行的继续
            if line.startswith(' ') or line.startswith('\t'):
                if buffer:
                    buffer += line.lstrip()
                else:
                    # 不应该发生，但处理这种情况
                    buffer = line.lstrip()
            else:
                if buffer:
                    unfolded.append(buffer)
                buffer = line
        
        if buffer:
            unfolded.append(buffer)
        
        return unfolded
    
    def parse_vcf_file(self, file_path: str) -> List[Contact]:
        """解析VCF文件"""
        print(f"正在读取文件: {file_path}")
        
        try:
            # 读取文件
            lines = self.read_vcf_file(file_path)
            
            # 处理折叠行
            original_line_count = len(lines)
            lines = self.unfold_lines(lines)
            print(f"折叠行处理: {original_line_count} -> {len(lines)} 行")
            
            # 解析vCard
            contacts = []
            current_contact = None
            current_block = []
            vcard_count = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.upper().startswith('BEGIN:VCARD'):
                    current_contact = Contact()
                    current_block = []
                    vcard_count += 1
                elif line.upper().startswith('END:VCARD'):
                    if current_contact:
                        self.process_vcard_block(current_block, current_contact)
                        contacts.append(current_contact)
                        
                        # 显示进度
                        if len(contacts) % 100 == 0:
                            print(f"  已解析 {len(contacts)} 个联系人...")
                    
                    current_contact = None
                    current_block = []
                elif current_contact:
                    current_block.append(line)
            
            print(f"找到 {vcard_count} 个vCard块，成功解析 {len(contacts)} 个联系人")
            self.contacts = contacts
            return contacts
            
        except Exception as e:
            print(f"❌ 解析VCF文件失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def process_vcard_block(self, lines: List[str], contact: Contact):
        """处理单个vCard块"""
        for line in lines:
            field_name, params, value = self.parse_field(line)
            
            if not field_name or not value:
                continue
            
            # 记录字段统计
            self.field_stats[field_name] += 1
            
            # 根据字段类型处理
            if field_name == 'VERSION':
                contact.version = value
            elif field_name == 'FN':
                contact.full_name = value
            elif field_name == 'N':
                self.parse_name_field(value, contact)
            elif field_name == 'TEL':
                phone_type = params.get('TYPE', 'OTHER')
                contact.add_phone(phone_type, value)
            elif field_name == 'EMAIL':
                contact.emails.append(value)
            elif field_name == 'ORG':
                self.parse_org_field(value, contact)
            elif field_name == 'TITLE':
                contact.title = value
            elif field_name == 'ADR':
                self.parse_address_field(value, params, contact)
            elif field_name == 'NOTE':
                contact.note += f"{value}\n"
            elif field_name == 'BDAY':
                contact.birthday = value
            elif field_name == 'URL':
                contact.urls.append(value)
            elif field_name == 'CATEGORIES':
                contact.categories = [cat.strip() for cat in value.split(',')]
            elif field_name == 'NICKNAME':
                contact.nickname = value
            elif field_name == 'GENDER':
                contact.gender = value
            elif field_name == 'UID':
                contact.uid = value
            elif field_name == 'X-DEPARTMENT':
                contact.department = value
            elif field_name == 'X-ANNIVERSARY':
                contact.anniversary = value
            elif field_name == 'PHOTO':
                contact.photo = "[图片数据]"
            else:
                # 其他字段保存到extra_fields
                contact.extra_fields[field_name] = value
            
            # 保存原始数据
            contact.raw_data[field_name] = line
    
    def parse_name_field(self, value: str, contact: Contact):
        """解析N字段（结构化姓名）"""
        # 格式: 姓氏;名字;中间名;前缀;后缀
        parts = value.split(';')
        parts = [part.strip() for part in parts]
        
        if len(parts) >= 1:
            contact.last_name = parts[0]
        if len(parts) >= 2:
            contact.first_name = parts[1]
        if len(parts) >= 3:
            contact.middle_name = parts[2]
        if len(parts) >= 4:
            contact.prefix = parts[3]
        if len(parts) >= 5:
            contact.suffix = parts[4]
        
        # 如果没有全名，尝试组合
        if not contact.full_name:
            name_parts = []
            if contact.prefix:
                name_parts.append(contact.prefix)
            if contact.last_name:
                name_parts.append(contact.last_name)
            if contact.first_name:
                name_parts.append(contact.first_name)
            if contact.middle_name:
                name_parts.append(contact.middle_name)
            if contact.suffix:
                name_parts.append(contact.suffix)
            
            contact.full_name = ''.join(name_parts)
    
    def parse_org_field(self, value: str, contact: Contact):
        """解析ORG字段"""
        # 格式: 公司;部门;...
        parts = value.split(';')
        parts = [part.strip() for part in parts]
        
        if len(parts) >= 1:
            contact.company = parts[0]
        if len(parts) >= 2:
            contact.department = parts[1]
    
    def parse_address_field(self, value: str, params: Dict[str, str], contact: Contact):
        """解析ADR字段"""
        # 格式: ;;;街道;城市;省份;邮编;国家
        parts = value.split(';')
        parts = [part.strip() for part in parts]
        
        address_dict = {
            'po_box': parts[0] if len(parts) > 0 else '',
            'extended': parts[1] if len(parts) > 1 else '',
            'street': parts[2] if len(parts) > 2 else '',
            'city': parts[3] if len(parts) > 3 else '',
            'region': parts[4] if len(parts) > 4 else '',
            'postal_code': parts[5] if len(parts) > 5 else '',
            'country': parts[6] if len(parts) > 6 else '',
        }
        
        # 格式化地址字符串
        address_parts = []
        if address_dict['street']:
            address_parts.append(address_dict['street'])
        if address_dict['city']:
            address_parts.append(address_dict['city'])
        if address_dict['region']:
            address_parts.append(address_dict['region'])
        if address_dict['postal_code']:
            address_parts.append(address_dict['postal_code'])
        if address_dict['country']:
            address_parts.append(address_dict['country'])
        
        formatted_address = ' '.join(address_parts)
        
        # 根据类型分配到不同地址字段
        address_type = params.get('TYPE', 'HOME').upper()
        
        if 'WORK' in address_type:
            contact.address_work = address_dict
            contact.address_work['formatted'] = formatted_address
        elif 'HOME' in address_type:
            contact.address_home = address_dict
            contact.address_home['formatted'] = formatted_address
        else:
            contact.address_other = address_dict
            contact.address_other['formatted'] = formatted_address
    
    def create_dataframe(self) -> pd.DataFrame:
        """将联系人转换为DataFrame"""
        if not self.contacts:
            return pd.DataFrame()
        
        data = []
        
        for contact in self.contacts:
            # 基础信息
            row = {
                '姓名': contact.full_name,
                '姓氏': contact.last_name,
                '名字': contact.first_name,
                '中间名': contact.middle_name,
                '昵称': contact.nickname,
                '性别': contact.gender,
            }
            
            # 电话信息
            row['手机'] = '; '.join(contact.mobile) if contact.mobile else ""
            row['工作电话'] = '; '.join(contact.tel_work) if contact.tel_work else ""
            row['家庭电话'] = '; '.join(contact.tel_home) if contact.tel_home else ""
            row['其他电话'] = '; '.join(contact.tel_other) if contact.tel_other else ""
            row['传真'] = '; '.join(contact.fax) if contact.fax else ""
            row['所有电话'] = contact.get_all_phones_formatted()
            
            # 职业信息
            row['公司'] = contact.company
            row['部门'] = contact.department
            row['职位'] = contact.title
            
            # 联系信息
            row['邮箱'] = '; '.join(contact.emails) if contact.emails else ""
            row['网址'] = '; '.join(contact.urls) if contact.urls else ""
            
            # 地址信息
            row['家庭地址'] = contact.address_home.get('formatted', '') if contact.address_home else ""
            row['工作地址'] = contact.address_work.get('formatted', '') if contact.address_work else ""
            row['其他地址'] = contact.address_other.get('formatted', '') if contact.address_other else ""
            
            # 个人资料
            row['生日'] = contact.birthday
            row['纪念日'] = contact.anniversary
            row['备注'] = contact.note.strip()
            row['分组'] = '; '.join(contact.categories) if contact.categories else ""
            
            # 其他
            row['vCard版本'] = contact.version
            row['唯一标识'] = contact.uid
            
            # 处理地址详情
            if contact.address_home:
                row['家庭街道'] = contact.address_home.get('street', '')
                row['家庭城市'] = contact.address_home.get('city', '')
                row['家庭省份'] = contact.address_home.get('region', '')
                row['家庭邮编'] = contact.address_home.get('postal_code', '')
                row['家庭国家'] = contact.address_home.get('country', '')
            
            if contact.address_work:
                row['工作街道'] = contact.address_work.get('street', '')
                row['工作城市'] = contact.address_work.get('city', '')
                row['工作省份'] = contact.address_work.get('region', '')
                row['工作邮编'] = contact.address_work.get('postal_code', '')
                row['工作国家'] = contact.address_work.get('country', '')
            
            # 添加扩展字段（按字母排序）
            extra_keys = sorted(contact.extra_fields.keys())
            for key in extra_keys:
                value = contact.extra_fields[key]
                if isinstance(value, str) and len(value) > 32767:
                    value = value[:32000] + "...[截断]"
                row[key] = value
            
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 重新排列列顺序（基础列在前）
        column_order = [
            # 基础信息
            '姓名', '姓氏', '名字', '中间名', '昵称', '性别',
            
            # 联系方式
            '手机', '工作电话', '家庭电话', '其他电话', '传真', '所有电话',
            
            # 职业信息
            '公司', '部门', '职位',
            
            # 联系信息
            '邮箱', '网址',
            
            # 地址信息
            '家庭地址', '工作地址', '其他地址',
            '家庭街道', '家庭城市', '家庭省份', '家庭邮编', '家庭国家',
            '工作街道', '工作城市', '工作省份', '工作邮编', '工作国家',
            
            # 个人资料
            '生日', '纪念日', '备注', '分组',
            
            # 其他
            'vCard版本', '唯一标识',
        ]
        
        # 只保留存在的列
        existing_columns = [col for col in column_order if col in df.columns]
        
        # 添加扩展字段
        extra_columns = [col for col in df.columns if col not in existing_columns]
        
        return df[existing_columns + sorted(extra_columns)]
    
    def save_to_excel(self, excel_file: str, include_raw_data: bool = False) -> Tuple[str, int]:
        """保存为Excel文件"""
        if not self.contacts:
            print("❌ 没有联系人数据可以保存")
            return "", 0
        
        try:
            # 确保文件扩展名
            if not excel_file.lower().endswith(('.xlsx', '.xls')):
                excel_file += '.xlsx'
            
            print(f"正在生成Excel文件...")
            
            # 创建主数据表
            df = self.create_dataframe()
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # 写入主数据
                df.to_excel(writer, sheet_name='通讯录', index=False)
                
                # 写入统计信息
                stats_data = {
                    '统计项': ['总联系人', '检测字段数', 'Quoted-Printable解码', 'Base64解码'],
                    '数量': [
                        len(self.contacts),
                        len(self.field_stats),
                        self.encoding_stats.get('quoted_printable', 0),
                        self.encoding_stats.get('base64', 0),
                    ]
                }
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='统计信息', index=False)
                
                # 写入字段统计
                if self.field_stats:
                    field_stats_data = {
                        '字段名': list(self.field_stats.keys()),
                        '出现次数': list(self.field_stats.values()),
                    }
                    field_stats_df = pd.DataFrame(field_stats_data)
                    field_stats_df = field_stats_df.sort_values('出现次数', ascending=False)
                    field_stats_df.to_excel(writer, sheet_name='字段统计', index=False)
                
                # 如果需要原始数据
                if include_raw_data and len(self.contacts) <= 1000:  # 限制数量避免文件过大
                    raw_data = []
                    for contact in self.contacts:
                        raw_row = {'姓名': contact.full_name}
                        for key, value in contact.raw_data.items():
                            # 截断过长的值
                            if isinstance(value, str) and len(value) > 32767:
                                value = value[:32000] + "...[截断]"
                            raw_row[key] = value
                        raw_data.append(raw_row)
                    
                    raw_df = pd.DataFrame(raw_data)
                    raw_df.to_excel(writer, sheet_name='原始数据', index=False)
                
                # 自动调整列宽
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                cell_value = str(cell.value) if cell.value else ""
                                # 考虑中文字符
                                chinese_count = sum(1 for c in cell_value if '\u4e00' <= c <= '\u9fff')
                                adjusted_length = len(cell_value) + chinese_count
                                max_length = max(max_length, adjusted_length)
                            except:
                                pass
                        
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            file_size = os.path.getsize(excel_file)
            print(f"✅ Excel文件保存成功: {excel_file}")
            print(f"   保存记录数: {len(df)}")
            print(f"   总列数: {len(df.columns)}")
            print(f"   文件大小: {file_size:,} 字节")
            
            # 显示统计
            self.show_statistics()
            
            # 显示数据预览
            self.show_data_preview(df)
            
            return excel_file, len(df)
            
        except Exception as e:
            print(f"❌ 保存Excel文件失败: {e}")
            import traceback
            traceback.print_exc()
            return "", 0
    
    def show_statistics(self):
        """显示转换统计"""
        print("\n📊 转换统计:")
        print("-" * 60)
        print(f"  总联系人: {len(self.contacts)}")
        print(f"  检测字段数: {len(self.field_stats)}")
        print(f"  Quoted-Printable解码: {self.encoding_stats.get('quoted_printable', 0)}")
        print(f"  Base64解码: {self.encoding_stats.get('base64', 0)}")
        
        if self.field_stats:
            print(f"\n  📈 字段出现频率 (前10):")
            sorted_stats = sorted(self.field_stats.items(), key=lambda x: x[1], reverse=True)[:10]
            for field_name, count in sorted_stats:
                print(f"    {field_name}: {count}次")
    
    def show_data_preview(self, df: pd.DataFrame):
        """显示数据预览"""
        print("\n📄 数据预览 (前5个联系人):")
        print("-" * 80)
        
        if len(df) > 0:
            # 显示关键列
            key_columns = ['姓名', '手机', '工作电话', '家庭电话', '公司', '职位', '邮箱', '分组']
            existing_columns = [col for col in key_columns if col in df.columns]
            
            if existing_columns:
                preview_df = df.head(5)[existing_columns]
                print(preview_df.to_string(index=False))
            else:
                print("无关键字段数据")
        else:
            print("无数据可显示")
        
        print("-" * 80)
    
    def convert(self, vcf_file: str, excel_file: str = None, include_raw_data: bool = False) -> Tuple[str, int]:
        """主转换方法"""
        try:
            if not os.path.exists(vcf_file):
                print(f"❌ 文件不存在: {vcf_file}")
                return "", 0
            
            # 解析VCF文件
            contacts = self.parse_vcf_file(vcf_file)
            
            if not contacts:
                print("❌ 没有找到有效的联系人数据")
                return "", 0
            
            # 生成输出文件名
            if excel_file is None:
                base_name = os.path.splitext(vcf_file)[0]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                excel_file = f"{base_name}_转换_{timestamp}.xlsx"
            else:
                if not excel_file.lower().endswith(('.xlsx', '.xls')):
                    excel_file += '.xlsx'
                
                # 如果只提供了文件名，使用VCF文件所在目录
                if os.path.dirname(excel_file) == "":
                    vcf_dir = os.path.dirname(os.path.abspath(vcf_file))
                    excel_file = os.path.join(vcf_dir, excel_file)
            
            # 保存为Excel
            return self.save_to_excel(excel_file, include_raw_data)
            
        except Exception as e:
            print(f"❌ 转换过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return "", 0


def main():
    """命令行主函数"""
    print("=" * 70)
    print("vCard转Excel通讯录转换器 v2.2")
    print("修复版 | 专为中文环境优化 | 支持完整字段提取 | 智能电话分类")
    print("=" * 70)
    
    # 输入文件路径
    vcf_file = input("请输入vcf文件路径: ").strip().strip('"')
    
    if not os.path.exists(vcf_file):
        print("❌ 错误: 文件不存在，请检查路径")
        return
    
    # 配置选项
    print("\n⚙️  转换选项:")
    print("  1. 自动编码检测")
    print("  2. UTF-8编码")
    print("  3. GBK编码")
    
    choice = input("选择编码方式 (1-3, 默认1): ").strip() or '1'
    
    if choice == '2':
        encoding = 'utf-8'
    elif choice == '3':
        encoding = 'gbk'
    else:
        encoding = 'auto'
    
    # 解码选项
    decode_qp_input = input("解码Quoted-Printable编码? (Y/n, 默认Y): ").strip().lower()
    decode_qp = not (decode_qp_input in ['n', 'no'])
    
    # 原始数据选项
    include_raw_input = input("包含原始vCard数据? (y/N, 默认N): ").strip().lower()
    include_raw_data = include_raw_input in ['y', 'yes']
    
    # 输出文件名
    vcf_dir = os.path.dirname(os.path.abspath(vcf_file))
    base_name = os.path.splitext(os.path.basename(vcf_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_excel = f"{base_name}_转换_{timestamp}.xlsx"
    default_path = os.path.join(vcf_dir, default_excel)
    
    output_file = input(f"输出Excel文件路径 (回车默认: {default_path}): ").strip().strip('"')
    if not output_file:
        output_file = default_path
    
    print(f"\n🎯 转换配置:")
    print(f"  输入文件: {vcf_file}")
    print(f"  输出文件: {output_file}")
    print(f"  编码方式: {encoding}")
    print(f"  解码QP: {'是' if decode_qp else '否'}")
    print(f"  原始数据: {'是' if include_raw_data else '否'}")
    
    print("\n🚀 开始转换...")
    
    # 创建转换器
    converter = VCFToExcelConverter(encoding=encoding, decode_qp=decode_qp)
    
    # 执行转换
    result_file, count = converter.convert(vcf_file, output_file, include_raw_data)
    
    if result_file and count > 0:
        print(f"\n✅ 转换成功完成!")
        print(f"   文件位置: {result_file}")
        print(f"   联系人数量: {count}")
        
        # 询问是否打开文件
        try:
            open_file = input("\n是否打开文件所在目录? (y/N, 默认N): ").strip().lower()
            if open_file in ['y', 'yes']:
                file_dir = os.path.dirname(result_file)
                if os.name == 'nt':  # Windows
                    os.system(f'explorer /select,"{result_file}"')
                elif os.name == 'posix':  # macOS/Linux
                    if sys.platform == 'darwin':  # macOS
                        os.system(f'open -R "{result_file}"')
                    else:  # Linux
                        os.system(f'xdg-open "{file_dir}"')
                print("已打开文件目录")
        except:
            print("无法自动打开目录")
    else:
        print("❌ 转换失败")


def quick_convert(vcf_file: str, excel_file: str = None, **kwargs) -> Tuple[str, int]:
    """
    快速转换函数
    
    参数:
        vcf_file: VCF文件路径
        excel_file: 输出Excel文件路径 (可选)
        **kwargs: 其他参数
            encoding: 编码方式 (默认'auto')
            decode_qp: 是否解码QP (默认True)
            include_raw_data: 是否包含原始数据 (默认False)
    
    返回:
        (Excel文件路径, 联系人数量)
    """
    encoding = kwargs.get('encoding', 'auto')
    decode_qp = kwargs.get('decode_qp', True)
    include_raw_data = kwargs.get('include_raw_data', False)
    
    converter = VCFToExcelConverter(encoding=encoding, decode_qp=decode_qp)
    return converter.convert(vcf_file, excel_file, include_raw_data)


# 使用示例
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")