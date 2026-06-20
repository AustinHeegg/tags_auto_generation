import os
import xml.etree.ElementTree as ET
from typing import Iterable, Dict, Set, Tuple

def get_projects_from_code_xml(manifest_dir: str, product_dir: str) -> Iterable[Dict]:
    """
    projects 合并：
    1) 保留原逻辑：遍历 manifest_dir 下的子目录，读取每个子目录下的 code.xml
    2) 新增逻辑：读取 manifest_dir/code/{product_dir}/code.xml
    """
    projects = []

    # 1) 原逻辑：遍历 manifest_dir 下的子目录读取 code.xml
    for item in os.listdir(manifest_dir):
        folder_path = os.path.join(manifest_dir, item)
        if not os.path.isdir(folder_path):
            continue

        code_xml_path = os.path.join(folder_path, "code.xml")
        if not os.path.exists(code_xml_path):
            continue

        tree = ET.parse(code_xml_path)
        root_xml = tree.getroot()
        for proj in root_xml.findall(".//project"):
            projects.append(proj.attrib)

    # 2) 新增逻辑：读取 manifest_dir/code/{product_dir}/code.xml
    target_code_xml = os.path.join(manifest_dir, "code", product_dir, "code.xml")
    if not os.path.exists(target_code_xml):
        raise FileNotFoundError(f"未找到指定目录的 code.xml：{target_code_xml}")

    tree = ET.parse(target_code_xml)
    root_xml = tree.getroot()
    for proj in root_xml.findall(".//project"):
        projects.append(proj.attrib)

    return projects

def extract_lt_project_names(code_projects: Iterable[Dict]) -> Set[str]:
    """从 code.xml 读取到的 project attrib 中提取 name，并过滤以 LT 开头。"""
    names = set()
    for proj in code_projects:
        name = proj.get("name")
        if name and name.startswith("LT"):
            names.add(name)
    return names

def get_project_names_from_release_note(release_note_path: str) -> Set[str]:
    """从 releaseNote.xml 中提取 project/@name，过滤以 LT 开头。"""
    tree = ET.parse(release_note_path)
    root_xml = tree.getroot()

    names = set()
    for proj in root_xml.findall(".//project"):
        name = proj.attrib.get("name")
        if name and name.startswith("LT"):
            names.add(name)
    return names

def compare_sets(a: Set[str], b: Set[str]) -> Tuple[Set[str], Set[str]]:
    """返回 (only_in_a, only_in_b)。"""
    return a - b, b - a

def print_names(title: str, names: Iterable[str]) -> None:
    print(title)
    names = list(names)
    if names:
        for name in sorted(names):
            print(name)
    else:
        print(" （无）")
    print()

def compare_manifest_and_release_note(manifest_dir: str, product_dir: str, release_note_path: str) -> None:
    code_projects = get_projects_from_code_xml(manifest_dir, product_dir)
    code_names = extract_lt_project_names(code_projects)
    release_names = get_project_names_from_release_note(release_note_path)

    only_in_manifest, only_in_release = compare_sets(code_names, release_names)

    print_names("仅在manifest中存在的项目名称:", only_in_manifest)
    print_names("仅在releaseNote.xml中存在的项目名称:", only_in_release)