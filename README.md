# main.py
import pandas as pd
import json
import argparse
import os
from releasenotes_parse import *
from sync_repo_and_tag import *
from validations import validate_version_format
from version_update import *

def main():
    parser = argparse.ArgumentParser(description="通过JSON配置文件更新Tag点Excel版本")
    parser.add_argument("-c", "--config", required=True, help="配置JSON文件路径")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    release_note_path = os.path.normpath(config.get("releaseNote"))
    tag_excel_path = os.path.normpath(config.get("tagExcel"))
    b_version = config.get("bVersion")
    hpmc_version = config.get("hpmcVersion")
    output_path = os.path.normpath(config.get("output", "files/updated_tag_points.xlsx"))

    try:
        validate_version_format(b_version, "bVersion")
        validate_version_format(hpmc_version, "hpmcVersion")
    except ValueError as e:
        print(f"配置文件校验错误: {e}")
        return

    print(f"\n{'='*60}\n解析 ReleaseNote：{release_note_path}")
    release_projects = parse_release_note(release_note_path)

    print(f"\n读取 Tag点Excel：{tag_excel_path}\n{'='*60}")
    df_tag = pd.read_excel(tag_excel_path)

    prefix = "https://repo-codeartsx-cn-southwest-2.sicarrier.com/"
    excel_projects = [
        val[len(prefix):] if isinstance(val, str) and val.startswith(prefix) else None
        for val in df_tag.iloc[:, 0]
    ]

    print("\n>>> 初次对比差异 >>>")
    compare_lists_release_excel(release_projects, [p for p in excel_projects if p])

    print(f"\n{'='*60}\n自动同步Excel和ReleaseNote中（删除多余，新增缺失）...\n{'='*60}")
    df_tag = sync_excel_with_release(df_tag, release_projects, b_version, hpmc_version)

    excel_projects_after_sync = [
        val[len(prefix):] if isinstance(val, str) and val.startswith(prefix) else None
        for val in df_tag.iloc[:, 0]
    ]
    print("\n>>> 自动同步后，再次校验差异 >>>")
    compare_lists_release_excel(release_projects, [p for p in excel_projects_after_sync if p])

    print(f"\n{'='*60}\n版本号替换处理中...\n{'='*60}")
    updated_df = update_versions(df_tag, b_version, hpmc_version)

    updated_df.to_excel(output_path, index=False)
    print(f"\n已保存更新后的Tag点表格到：{output_path}\n{'='*60}")

if __name__ == "__main__":
    main()

# releasenotes_parse.py
import re

def parse_release_note(file_path):
    project_names = []
    pattern = re.compile(r'<project name="([^"]+)"')
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                name = match.group(1)
                if not name.startswith("LT-"):
                    continue
                if name.startswith("LT-HCS/"):
                    continue
                if name.endswith('.git'):
                    name = name[:-4]
                project_names.append(name)
    return project_names



# sync_repo_and_tag.py
import pandas as pd

def compare_lists_release_excel(release_projects, excel_projects):
    set1 = set(release_projects)
    set2 = set(excel_projects)

    only_in_1 = set1 - set2
    only_in_2 = set2 - set1

    print("\n--- 只在ReleaseNote中存在的项目 ---")
    if only_in_1:
        print("\n".join(sorted(only_in_1)))
    else:
        print("")

    print("\n--- 只在Excel中存在的项目 ---")
    if only_in_2:
        print("\n".join(sorted(only_in_2)))
    else:
        print("")

def sync_excel_with_release(df, release_projects, b_version, hpmc_version):
    prefix = "https://repo-codeartsx-cn-southwest-2.sicarrier.com/"

    def extract_project_name(val):
        if isinstance(val, str) and val.startswith(prefix):
            return val[len(prefix):]
        return None

    def extract_component_name(project_name):
        parts = project_name.split('/')
        if len(parts) >= 3:
            return parts[2]
        return ""

    excel_projects = df.iloc[:, 0].map(extract_project_name)
    release_set = set(release_projects)
    excel_set = set(excel_projects.dropna())

    only_in_release = release_set - excel_set
    only_in_excel = excel_set - release_set

    print("\n--- 待删除Excel中多余项目 ---")
    if only_in_excel:
        print("\n".join(sorted(only_in_excel)))
    else:
        print("")

    print("\n--- 待新增Excel中缺失项目 ---")
    if only_in_release:
        print("\n".join(sorted(only_in_release)))
    else:
        print("")

    df = df[~df.iloc[:, 0].map(extract_project_name).isin(only_in_excel)].copy()

    template_row = df.iloc[0] if not df.empty else None

    new_rows = []
    for proj in only_in_release:
        new_row = []
        new_row.append(prefix + proj)

        proj_lower = proj.lower()
        if "testbench" in proj_lower or "devbench" in proj_lower:
            tag_prefix = "TestBench"
        else:
            tag_prefix = extract_component_name(proj)

        if "HPMC" in proj:
            new_tag = f"tag_HPMC_V100R001C10{hpmc_version}_XY_Alpha1{b_version}"
        else:
            new_tag = f"tag_{tag_prefix}_V100R001C10{b_version}"

        new_row.append(new_tag)

        if template_row is not None:
            for i in range(2, len(template_row)):
                new_row.append(template_row.iat[i])
        else:
            new_row.extend([""] * (df.shape[1] - 2))

        new_rows.append(new_row)

    if new_rows:
        new_df = pd.DataFrame(new_rows, columns=df.columns)
        df = pd.concat([df, new_df], ignore_index=True)

    return df


# validations.py
import re

def validate_version_format(version_str, name):
    if version_str is None or version_str == "":
        return
    if not isinstance(version_str, str):
        raise ValueError(f"{name} 必须是字符串")
    if not re.fullmatch(r'B\d{3}', version_str):
        raise ValueError(f"{name} 格式错误，应为 'B' 加三位数字，如 B060，当前值：{version_str}")


# version_update.py
import re

def update_versions(df, b_version=None, hpmc_version=None):
    b_pattern = re.compile(r'B\d{3}')
    printed_hpmc = False
    printed_b = False
    for idx, row in df.iterrows():
        tag_str = str(row.iloc[1])
        code_repo = str(row.iloc[0])
        if not tag_str:
            continue
        
        if "HPMC" in code_repo:
            matches = list(b_pattern.finditer(tag_str))
            if len(matches) >= 2:
                old_hpmc_version = tag_str[matches[0].start():matches[0].end()]
                old_b_version = tag_str[matches[1].start():matches[1].end()]
                start1, end1 = matches[0].span()
                start2, end2 = matches[1].span()
                if hpmc_version:
                    new_tag = (
                        tag_str[:start1] + hpmc_version +
                        tag_str[end1:start2] + b_version +
                        tag_str[end2:]
                    )
                    if not printed_hpmc:
                        print(f"--- HPMC版本替换示例 ---\n原HPMC版本号 {old_hpmc_version} 替换为 {hpmc_version}\n")
                        printed_hpmc = True
                else:
                    new_tag = (
                        tag_str[:start1] + old_hpmc_version +
                        tag_str[end1:start2] + b_version +
                        tag_str[end2:]
                    )
                    if not printed_hpmc:
                        print(f"--- HPMC版本无变更示例 ---\n保持原HPMC版本号 {old_hpmc_version}\n")
                        printed_hpmc = True
                df.loc[idx, df.columns[1]] = new_tag
                if not printed_b:
                    print(f"--- B版本替换示例 ---\n原B版本号 {old_b_version} 替换为 {b_version}\n")
                    printed_b = True
            else:
                print(f"HPMC仓tag格式异常，未找到足够的版本号Bxxx")
        else:
            match = b_pattern.search(tag_str)
            if match:
                old_b_version = match.group()
                new_tag, count = b_pattern.subn(b_version, tag_str, count=1)
                if count == 1:
                    df.loc[idx, df.columns[1]] = new_tag
                    if not printed_b:
                        print(f"\n--- B版本替换示例 ---\n原B版本号 {old_b_version} 替换为 {b_version}\n")
                        printed_b = True
                else:
                    print(f"非HPMC仓tag格式异常，未找到B版本号Bxxx")
            else:
                print(f"非HPMC仓tag格式异常，未找到B版本号Bxxx")
    return df
