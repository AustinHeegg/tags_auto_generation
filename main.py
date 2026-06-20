import pandas as pd
import json
import argparse
import os
from releasenotes_parse import parse_release_note
from sync_repo_and_tag import compare_lists_release_excel, sync_excel_with_release
from validations import validate_version_format
from version_update import update_versions
from comp_manifest_releasenotes import compare_manifest_and_release_note
from update_manifest_revision import update_manifest_code_xmls, update_helf_revision_by_release_notes
from format_check import format_targets

# 打印模块化标题框：用于区分不同阶段输出
def print_block(title: str) -> None:
    bar = "=" * 85
    # 清理不可见字符：去首尾空白，并把换行/Tab 变成空格
    title = title.replace("\t", " ").replace("\n", " ").strip()
    if len(title) > 85:
        title = title[:85]
    mid = title.center(85)
    print(bar)
    print(mid)
    print(bar)

def main():
    # ========== 参数解析 ==========
    parser = argparse.ArgumentParser(description="通过JSON配置文件更新Tag点Excel版本")
    parser.add_argument("-c", "--config", required=True, help="配置JSON文件路径")
    args = parser.parse_args()

    # ========== 读取配置 ==========
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    release_note_path = os.path.normpath(config.get("releaseNote"))
    tag_excel_path = os.path.normpath(config.get("tagExcel"))
    b_version = config.get("bVersion")
    hpmc_version = config.get("hpmcVersion")
    output_path = os.path.normpath(config.get("output", "files/updated_tag_points.xlsx"))

    # manifest 对比相关入参（是否启用取决于 manifestDir 是否存在）
    manifest_dir = config.get("manifestDir")
    manifest_dir = os.path.normpath(manifest_dir) if manifest_dir else None
    product_dir = config.get("product_dir")  # master/top/bot/opt

    # ========== 版本号格式校验 ==========
    try:
        validate_version_format(b_version, "bVersion")
        validate_version_format(hpmc_version, "hpmcVersion")
    except ValueError as e:
        print(f"配置文件校验错误: {e}")
        return

    # ========== 解析 ReleaseNote ==========
    print(f"\n{'='*85}\n解析 ReleaseNote：{release_note_path}")
    release_projects = parse_release_note(release_note_path)

    # ========== manifest 与 ReleaseNote 差集对比（仅打印） ==========
    if manifest_dir:
        print_block("对比 manifest 与 ReleaseNote（仅打印差集）")
        if not product_dir:
            print("未在配置中提供 product_dir，无法选择 code.xml 目录（master/top/bot/opt）。")
            return
        compare_manifest_and_release_note(manifest_dir, product_dir, release_note_path)
    else:
        print("\n未在配置中提供 manifestDir，跳过 manifest vs releaseNote 对比。")

    # ========== 读取 Tag点 Excel ==========
    print(f"\n读取 Tag点Excel：{tag_excel_path}\n{'='*85}")
    df_tag = pd.read_excel(tag_excel_path)

    # 从 Excel 第一列提取项目名（去掉前缀 URL）
    prefix = "https://repo-codeartsx-cn-southwest-2.sicarrier.com/"
    excel_projects = [
        val[len(prefix):] if isinstance(val, str) and val.startswith(prefix) else None
        for val in df_tag.iloc[:, 0]
    ]

    # ========== 初次对比（ReleaseNote vs Excel） ==========
    print_block("初次releasNotes和tag点excel对比差异")
    compare_lists_release_excel(release_projects, [p for p in excel_projects if p])

    # ========== 自动同步 Excel 与 ReleaseNote ==========
    print_block("自动同步Excel和ReleaseNote中（删除多余，新增缺失）")
    df_tag = sync_excel_with_release(df_tag, release_projects, b_version, hpmc_version)

    # 同步后再次计算 Excel 项目名（用于二次对比）
    excel_projects_after_sync = [
        val[len(prefix):] if isinstance(val, str) and val.startswith(prefix) else None
        for val in df_tag.iloc[:, 0]
    ]
    print_block("自动同步后，再次校验差异")
    compare_lists_release_excel(release_projects, [p for p in excel_projects_after_sync if p])

    # ========== 版本号替换 ==========
    print_block("版本号tag点替换处理中")
    updated_df = update_versions(df_tag, b_version, hpmc_version)

    # ========== 输出结果 Excel ==========
    updated_df.to_excel(output_path, index=False)
    print(f"\n已保存更新后的Tag点表格到：{output_path}")

    # ========== 更新 manifest code.xml revision（跳过 HELF） ==========
    if manifest_dir:
        if not product_dir:
            print("未在配置中提供 product_dir，无法更新 manifest 的 code.xml。")
            return

        print_block("更新 manifest code.xml revision（跳过 HELF）")

        import hashlib

        updated_files = 0
        changed_files = 0
        total_modified_projects = 0

        # update_manifest_code_xmls 内部会跳过 HELF，并返回（code_xml_path, modified_count）
        for code_xml_path, modified_count in update_manifest_code_xmls(
            manifest_dir, product_dir, b_version, hpmc_version
        ):
            updated_files += 1
            total_modified_projects += modified_count

            with open(code_xml_path, "rb") as f:
                after = f.read()

            if modified_count > 0:
                changed_files += 1
                print(f"[xml updated] {code_xml_path} modified_projects={modified_count}")

        if changed_files == 0:
            print("manifest中code.xml无变更")
        else:
            print(f"[xml done] 变更文件数={changed_files}, 共修改project数={total_modified_projects}（处理文件数={updated_files}）")

        # ========== 更新 HELF code.xml revision ==========
        print_block("更新 HELF code.xml revision")
        helf_modified = update_helf_revision_by_release_notes(
            manifest_dir=manifest_dir,
            release_note_path=release_note_path
        )
        if helf_modified == 0:
            print("HELF code.xml无变更")
        else:
            print(f"HELF code.xml已更新，修改project数={helf_modified}")
    print_block("\nmanifest code.xml 替换完成\n")

    format_targets(manifest_dir, product_dir)
    print("[format updated done]manifest code.xml 格式化完成\n")

if __name__ == "__main__":
    main()