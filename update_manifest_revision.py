import os
import re
from lxml import etree as ET

B_PATTERN = re.compile(r'B\d{3}')

def normalize_revision_spacing(revision: str) -> str:
    if revision is None:
        return revision
    revision = re.sub(r'\s+', ' ', revision)
    return revision.strip()

def update_revision_value(revision: str, is_hpmc_file: bool, b_version: str, hpmc_version: str) -> str:
    revision = normalize_revision_spacing(revision)
    matches = list(B_PATTERN.finditer(revision))
    if not matches:
        return revision

    if is_hpmc_file and len(matches) >= 2:
        m0 = matches[0]  # 第一个 Bxxx -> hpmcVersion
        m1 = matches[1]  # 第二个 Bxxx -> bVersion
        return (
            revision[:m0.start()] + hpmc_version +
            revision[m0.end():m1.start()] + b_version +
            revision[m1.end():]
        )

    # 非 HPMC（或 HPMC 但 B 不足）：替换第一个 Bxxx -> bVersion
    m0 = matches[0]
    return revision[:m0.start()] + b_version + revision[m0.end():]

def detect_newline_style_from_file(code_xml_path: str) -> str:
    with open(code_xml_path, "rb") as f:
        data = f.read()
    return "\r\n" if b"\r\n" in data else "\n"

def write_xml_preserve_newline(tree: ET._ElementTree, code_xml_path: str) -> None:
    newline = detect_newline_style_from_file(code_xml_path)

    xml_bytes = ET.tostring(
        tree,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False
    )

    xml_text = xml_bytes.decode("utf-8")
    xml_text = xml_text.replace("\r\n", "\n").replace("\r", "\n")
    xml_text = xml_text.replace("\n", newline)

    with open(code_xml_path, "wb") as f:
        f.write(xml_text.encode("utf-8"))

def is_hpmc_code_file(manifest_dir: str, code_xml_path: str) -> bool:
    hpmc_root = os.path.join(manifest_dir, "HPMC")
    return os.path.commonpath([os.path.abspath(code_xml_path), os.path.abspath(hpmc_root)]) == os.path.abspath(hpmc_root)

def update_code_xml_revisions(code_xml_path: str, manifest_dir: str, b_version: str, hpmc_version: str) -> int:
    """
    修改所有带 revision 属性的节点（包括 default/project 等）。
    但只替换其中 Bxxx 匹配的版本号；其它不动。
    """
    parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False)
    tree = ET.parse(code_xml_path, parser)
    root = tree.getroot()

    is_hpmc_file = is_hpmc_code_file(manifest_dir, code_xml_path)

    modified_count = 0

    # XPath：所有有 revision 属性的节点
    for elem in root.xpath("//*[@revision]"):
        revision = elem.get("revision")
        if not revision:
            continue

        new_revision = update_revision_value(revision, is_hpmc_file, b_version, hpmc_version)
        if new_revision != revision:
            elem.set("revision", new_revision)
            modified_count += 1

    write_xml_preserve_newline(tree, code_xml_path)
    return modified_count

def iter_target_code_xmls(manifest_dir: str, product_dir: str):
    """
    A: manifest_dir/code/<product_dir>/code.xml
    B: manifest_dir/<sub>/code.xml 但跳过 manifest_dir/HELF/code.xml
    """
    code_xml_a = os.path.join(manifest_dir, "code", product_dir, "code.xml")
    if not os.path.exists(code_xml_a):
        raise FileNotFoundError(f"未找到目标 A code.xml：{code_xml_a}")
    yield code_xml_a

    for item in os.listdir(manifest_dir):
        if item == "HELF":
            continue
        folder_path = os.path.join(manifest_dir, item)
        if not os.path.isdir(folder_path):
            continue
        code_xml_b = os.path.join(folder_path, "code.xml")
        if os.path.exists(code_xml_b):
            yield code_xml_b

def update_manifest_code_xmls(manifest_dir: str, product_dir: str, b_version: str, hpmc_version: str):
    """
    供 main.py 使用的便捷封装：
    yield (code_xml_path, modified_revision_count)
    """
    for code_xml_path in iter_target_code_xmls(manifest_dir, product_dir):
        modified_count = update_code_xml_revisions(
            code_xml_path, manifest_dir, b_version, hpmc_version
        )
        yield code_xml_path, modified_count

def update_helf_revision_by_release_notes(manifest_dir: str, release_note_path: str) -> int:
    """
    HELF 特殊处理：
    - 读取 releaseNotes：path -> upstream
    - 更新 manifest_dir/HELF/code.xml 中 project[@path] 匹配项的 revision -> upstream
    - 只做 revision 替换，不碰其它字段
    """
    helf_code_xml = os.path.join(manifest_dir, "HELF", "code.xml")
    if not os.path.exists(helf_code_xml):
        raise FileNotFoundError(f"未找到 HELF code.xml：{helf_code_xml}")

    parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False)

    # 1) 解析 releaseNotes 构建映射：path -> upstream
    rn_tree = ET.parse(release_note_path, parser)
    rn_root = rn_tree.getroot()

    path_to_upstream = {}
    for proj in rn_root.findall(".//project"):
        p = proj.get("path")
        u = proj.get("upstream")
        if p and u:
            path_to_upstream[p] = u

    # 2) 解析 HELF code.xml，按 path 替换 revision
    code_tree = ET.parse(helf_code_xml, parser)
    code_root = code_tree.getroot()

    modified_count = 0
    for proj in code_root.findall(".//project"):
        p = proj.get("path")
        if not p:
            continue
        if p in path_to_upstream:
            new_rev = path_to_upstream[p]
            old_rev = proj.get("revision")
            if new_rev != old_rev:
                proj.set("revision", new_rev)
                modified_count += 1

    write_xml_preserve_newline(code_tree, helf_code_xml)
    return modified_count