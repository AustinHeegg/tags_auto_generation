import re

def validate_version_format(version_str, name):
    if version_str is None or version_str == "":
        return
    if not isinstance(version_str, str):
        raise ValueError(f"{name} 必须是字符串")
    if not re.fullmatch(r'B\d{3}', version_str):
        raise ValueError(f"{name} 格式错误，应为 'B' 加三位数字，如 B060，当前值：{version_str}")
