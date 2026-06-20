import os
import re
from typing import List

ATTR_ORDER = ["remote", "path", "name", "revision", "groups"]

PROJECT_LINE_REGEX = re.compile(r'<project\s+([^>]*)\s*/?>')
ATTR_REGEX = re.compile(r'(\w+)="([^"]*)"')

def reorder_project_line(line: str):
    m = PROJECT_LINE_REGEX.search(line)
    if not m:
        return line, False

    attr_str = m.group(1)
    attrs = dict(ATTR_REGEX.findall(attr_str))

    # 删除 upstream 属性
    attrs.pop("upstream", None)

    # revision 不以 refs/tags/ 开头则删除
    rev = attrs.get("revision")
    if rev and not rev.startswith("refs/tags/"):
        attrs.pop("revision")

    # name 末尾添加 .git (如果没以 .git 结尾)
    name = attrs.get("name")
    if name and not name.endswith(".git"):
        attrs["name"] = name + ".git"

    new_attrs_parts = []
    for attr in ATTR_ORDER:
        if attr in attrs:
            val = attrs[attr]
            new_attrs_parts.append(f'{attr}="{val}"')

    new_attr_str = " ".join(new_attrs_parts)

    if attr_str.strip() == new_attr_str:
        return line, False

    start_pos = m.start(1)
    end_pos = m.end(1)

    new_line = line[:start_pos] + new_attr_str + line[end_pos:]

    new_line = new_line.rstrip(" >/\r\n\t") + "/>\n"
    return new_line, True

def process_code_xml_format(code_xml_path: str) -> None:
    changed = False
    with open(code_xml_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if "<project" in line:
            new_line, did_change = reorder_project_line(line)
            if did_change:
                changed = True
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    if changed:
        with open(code_xml_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"[format updated] {code_xml_path}")
    else:
        print(f"[format ok] {code_xml_path}")

def format_targets(manifest_dir: str, product_dir: str) -> int:
    """
    格式化：
    A: manifest_dir/code/<product_dir>/code.xml
    B: manifest_dir/*/code.xml（包含 HELF）
    返回：实际处理到的 code.xml 文件数
    """
    targets: List[str] = []

    # A
    a_path = os.path.join(manifest_dir, "code", product_dir, "code.xml")
    if os.path.exists(a_path):
        targets.append(a_path)

    # B
    for item in os.listdir(manifest_dir):
        folder_path = os.path.join(manifest_dir, item)
        if not os.path.isdir(folder_path):
            continue
        b_path = os.path.join(folder_path, "code.xml")
        if os.path.exists(b_path):
            targets.append(b_path)

    targets = sorted(set(targets))

    for t in targets:
        process_code_xml_format(t)

    return len(targets)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="format_check: 规范化 code.xml 中 project 属性顺序")
    parser.add_argument("--manifestDir", required=True, help="manifest_dir 根目录")
    parser.add_argument("--productDir", required=True, help="product_dir：master/top/bot/opt")
    args = parser.parse_args()

    n = format_targets(args.manifestDir, args.productDir)
    print(f"[format_check done] code.xml files={n}")

if __name__ == "__main__":
    main()