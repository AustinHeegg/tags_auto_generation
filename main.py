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
