import os
import xml.etree.ElementTree as ET
from typing import List, Dict

def parse_opensrc_projects_from_release(release_note_path: str) -> Dict[str, str]:
    """
    从ReleaseNote解析所有opensrc相关的项目
    判断条件：remote以"opensrc@"开头 或 groups中包含"opensrc"
    返回: {(name, path): upstream} 的字典
    """
    opensrc_dict = {}
    
    try:
        tree = ET.parse(release_note_path)
        root = tree.getroot()
        
        for project in root.findall('project'):
            remote = project.get('remote')
            groups = project.get('groups')
            
            # 判断是否为opensrc项目：remote以"opensrc@"开头 或 groups中包含"opensrc"
            is_opensrc = False
            
            # 检查remote
            if remote and remote.startswith('opensrc@'):
                is_opensrc = True
            
            # 检查groups
            if groups and 'opensrc' in groups.split(','):
                is_opensrc = True
            
            if is_opensrc:
                name = project.get('name')
                path = project.get('path')
                upstream = project.get('upstream')
                
                if name and path and upstream:
                    key = f"{name}|{path}"
                    opensrc_dict[key] = upstream
                    
    except Exception as e:
        print(f"解析ReleaseNote失败: {e}")
    
    return opensrc_dict


def find_opensource_xml_files(manifest_dir: str) -> List[str]:
    """
    查找manifest_dir下所有子文件夹中的opensource.xml文件
    """
    xml_files = []
    
    if not os.path.exists(manifest_dir):
        print(f"manifest目录不存在: {manifest_dir}")
        return xml_files
    
    for root, dirs, files in os.walk(manifest_dir):
        if 'opensource.xml' in files:
            xml_files.append(os.path.join(root, 'opensource.xml'))
    
    return xml_files


def update_opensrc_revisions(manifest_dir: str, release_note_path: str) -> None:
    """
    更新所有opensource.xml中与ReleaseNote不一致的revision
    使用ReleaseNote中的upstream值替换xml中的revision
    只修改<project>标签的revision属性，不修改<remote>标签
    """
    # 1. 从ReleaseNote获取所有opensrc项目的upstream
    release_opensrc = parse_opensrc_projects_from_release(release_note_path)
    
    if not release_opensrc:
        print("ReleaseNote中没有opensrc相关的项目")
        return
    
    # 2. 查找所有opensource.xml文件
    xml_files = find_opensource_xml_files(manifest_dir)
    
    if not xml_files:
        print("未找到任何opensource.xml文件")
        return
    
    # 3. 逐个处理opensource.xml
    total_updated = 0
    changed_files = 0
    processed_files = 0
    
    for xml_path in xml_files:
        processed_files += 1
        try:
            # 解析XML
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            updated_count = 0
            
            # 遍历所有project节点
            for project in root.findall('project'):
                name = project.get('name')
                path = project.get('path')
                
                if name and path:
                    key = f"{name}|{path}"
                    
                    # 如果这个项目在ReleaseNote中
                    if key in release_opensrc:
                        current_revision = project.get('revision')
                        expected_revision = release_opensrc[key]  # upstream的值
                        
                        # 如果不一致，则更新revision
                        if current_revision != expected_revision:
                            project.set('revision', expected_revision)
                            updated_count += 1
                            total_updated += 1
            
            # 如果有更新，保存文件并记录
            if updated_count > 0:
                tree.write(xml_path, encoding='utf-8', xml_declaration=True)
                changed_files += 1
                print(f"[opensource updated] {xml_path} modified_projects={updated_count}")
                
        except Exception as e:
            print(f"处理失败: {xml_path} - {e}")
    
    # 4. 输出汇总
    if changed_files == 0:
        print("opensource.xml无变更")
    else:
        print(f"[opensource done] 变更文件数={changed_files}, 共修改project数={total_updated}（处理文件数={processed_files}）")
    print("="*85)
