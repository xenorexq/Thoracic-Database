"""
字段验证器模块

提供详细的字段验证和错误提示功能，帮助用户快速定位输入错误。
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """验证错误信息"""
    field_name: str  # 字段名称
    field_label: str  # 字段显示标签
    error_message: str  # 错误消息
    current_value: Any  # 当前值


class PatientDataValidator:
    """患者数据验证器"""
    
    # 字段标签映射（用于友好的错误提示）
    FIELD_LABELS = {
        "hospital_id": "住院号",
        "cancer_type": "癌种",
        "sex": "性别",
        "birth_ym4": "出生年月",
        "pack_years": "吸烟包年数",
        "eso_from_incisors_cm": "距门齿距离",
        "nac_chemo_cycles": "新辅助化疗周期数",
        "nac_immuno_cycles": "新辅助免疫周期数",
        "nac_targeted_cycles": "新辅助靶向周期数",
        "nac_antiangio_cycles": "新辅助抗血管周期数",
        "nac_date": "新辅助治疗日期",
        "adj_chemo_cycles": "辅助化疗周期数",
        "adj_immuno_cycles": "辅助免疫周期数",
        "adj_targeted_cycles": "辅助靶向周期数",
        "adj_antiangio_cycles": "辅助抗血管周期数",
        "adj_date": "辅助治疗日期",
    }
    
    @staticmethod
    def validate_required_field(value: Any, field_name: str) -> Optional[ValidationError]:
        """验证必填字段"""
        if not value or str(value).strip() == "":
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message="此字段为必填项",
                current_value=value
            )
        return None
    
    @staticmethod
    def validate_birth_ym(value: str, field_name: str = "birth_ym4") -> Optional[ValidationError]:
        """验证出生年月（YYYYMM格式）"""
        if not value:
            return None  # 可选字段
        
        value = str(value).strip()
        
        # 检查是否为 "None" 字符串
        if value.lower() == "none":
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message="字段包含无效值 'None'，请清空或输入正确的出生年月（格式：YYYYMM）",
                current_value=value
            )
        
        # 验证格式
        if len(value) != 6 or not value.isdigit():
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message=f"格式错误，应为6位数字（YYYYMM），例如：199001",
                current_value=value
            )
        
        # 验证年份和月份范围
        year = int(value[:4])
        month = int(value[4:6])
        
        if year < 1900 or year > 2100:
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message=f"年份不合理（{year}），应在1900-2100之间",
                current_value=value
            )
        
        if month < 1 or month > 12:
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message=f"月份不合理（{month}），应在01-12之间",
                current_value=value
            )
        
        return None
    
    @staticmethod
    def validate_date6(value: str, field_name: str) -> Optional[ValidationError]:
        """验证日期（YYMMDD格式）"""
        if not value:
            return None  # 可选字段
        
        value = str(value).strip()
        
        # 检查是否为 "None" 字符串
        if value.lower() == "none":
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message="字段包含无效值 'None'，请清空或输入正确的日期（格式：YYMMDD）",
                current_value=value
            )
        
        # 验证格式
        if len(value) != 6 or not value.isdigit():
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message=f"格式错误，应为6位数字（YYMMDD），例如：250115",
                current_value=value
            )
        
        # 验证月份和日期范围
        month = int(value[2:4])
        day = int(value[4:6])
        
        if month < 1 or month > 12:
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message=f"月份不合理（{month}），应在01-12之间",
                current_value=value
            )
        
        if day < 1 or day > 31:
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message=f"日期不合理（{day}），应在01-31之间",
                current_value=value
            )
        
        return None
    
    @staticmethod
    def validate_number(value: str, field_name: str, allow_empty: bool = True) -> Optional[ValidationError]:
        """验证数字字段"""
        if not value or str(value).strip() == "":
            if allow_empty:
                return None
            else:
                return ValidationError(
                    field_name=field_name,
                    field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                    error_message="此字段不能为空",
                    current_value=value
                )
        
        value = str(value).strip()
        
        # 检查是否为 "None" 字符串
        if value.lower() == "none":
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message="字段包含无效值 'None'，请清空或输入正确的数字",
                current_value=value
            )
        
        # 验证是否为数字
        try:
            float(value)
        except ValueError:
            return ValidationError(
                field_name=field_name,
                field_label=PatientDataValidator.FIELD_LABELS.get(field_name, field_name),
                error_message=f"应为数字，当前值：{value}",
                current_value=value
            )
        
        return None
    
    @staticmethod
    def validate_patient_data(data: Dict[str, Any]) -> List[ValidationError]:
        """
        验证患者数据的所有字段
        
        Args:
            data: 患者数据字典
        
        Returns:
            验证错误列表，如果为空则表示验证通过
        """
        errors = []
        
        # 1. 必填字段验证
        required_fields = ["hospital_id", "cancer_type", "sex"]
        for field in required_fields:
            error = PatientDataValidator.validate_required_field(data.get(field), field)
            if error:
                errors.append(error)
        
        # 2. 出生年月验证
        birth = data.get("birth_ym4")
        if birth:
            birth_str = str(birth).strip()
            if birth_str and birth_str.lower() != "none":
                error = PatientDataValidator.validate_birth_ym(birth_str, "birth_ym4")
                if error:
                    errors.append(error)
        
        # 3. 数字字段验证
        number_fields = [
            "pack_years",
            "eso_from_incisors_cm",
            "nac_chemo_cycles",
            "nac_immuno_cycles",
            "nac_targeted_cycles",
            "nac_antiangio_cycles",
            "adj_chemo_cycles",
            "adj_immuno_cycles",
            "adj_targeted_cycles",
            "adj_antiangio_cycles",
        ]
        
        for field in number_fields:
            value = data.get(field)
            if value:
                value_str = str(value).strip()
                if value_str and value_str.lower() != "none":
                    error = PatientDataValidator.validate_number(value_str, field)
                    if error:
                        errors.append(error)
        
        # 4. 日期字段验证
        date_fields = [
            "nac_date",
            "adj_date",
        ]
        
        for field in date_fields:
            value = data.get(field)
            if value:
                value_str = str(value).strip()
                if value_str and value_str.lower() != "none":
                    error = PatientDataValidator.validate_date6(value_str, field)
                    if error:
                        errors.append(error)
        
        return errors
    
    @staticmethod
    def format_errors(errors: List[ValidationError]) -> str:
        """格式化错误列表为可读文本"""
        if not errors:
            return ""
        
        lines = ["发现以下字段错误：\n"]
        
        for i, error in enumerate(errors, 1):
            lines.append(f"{i}. 【{error.field_label}】")
            lines.append(f"   错误：{error.error_message}")
            if error.current_value is not None:
                lines.append(f"   当前值：{repr(error.current_value)}")
            lines.append("")
        
        lines.append("请修正上述错误后重新保存。")
        
        return "\n".join(lines)


def safe_str(value: Any) -> str:
    """
    安全地将值转换为字符串，避免显示 "None"
    
    Args:
        value: 任意值
    
    Returns:
        字符串（如果值为 None 或 "None"，返回空字符串）
    """
    if value is None:
        return ""
    
    value_str = str(value).strip()
    
    # 检查是否为 "None" 字符串
    if value_str.lower() == "none":
        return ""
    
    return value_str


