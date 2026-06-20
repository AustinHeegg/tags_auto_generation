import re

# 模块级去重：保证在同一进程生命周期内只打印一次示例
_PRINTED = {
    "hpmc_example": False,
    "b_example": False,
}

def update_versions(df, b_version=None, hpmc_version=None):
    b_pattern = re.compile(r'B\d{3}')

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
                    if not _PRINTED["hpmc_example"]:
                        print(f"--- HPMC版本替换示例 ---\n原HPMC版本号 {old_hpmc_version} 替换为 {hpmc_version}\n")
                        _PRINTED["hpmc_example"] = True
                else:
                    new_tag = (
                        tag_str[:start1] + old_hpmc_version +
                        tag_str[end1:start2] + b_version +
                        tag_str[end2:]
                    )
                    if not _PRINTED["hpmc_example"]:
                        print(f"--- HPMC版本无变更示例 ---\n保持原HPMC版本号 {old_hpmc_version}\n")
                        _PRINTED["hpmc_example"] = True

                df.loc[idx, df.columns[1]] = new_tag

                if not _PRINTED["b_example"]:
                    print(f"--- B版本替换示例 ---\n原B版本号 {old_b_version} 替换为 {b_version}\n")
                    _PRINTED["b_example"] = True
            else:
                print(f"HPMC仓tag格式异常，未找到足够的版本号Bxxx")
        else:
            match = b_pattern.search(tag_str)
            if match:
                old_b_version = match.group()
                new_tag, count = b_pattern.subn(b_version, tag_str, count=1)
                if count == 1:
                    df.loc[idx, df.columns[1]] = new_tag
                    if not _PRINTED["b_example"]:
                        print(f"\n--- B版本替换示例 ---\n原B版本号 {old_b_version} 替换为 {b_version}\n")
                        _PRINTED["b_example"] = True
                else:
                    print(f"非HPMC仓tag格式异常，未找到B版本号Bxxx")
            else:
                print(f"非HPMC仓tag格式异常，未找到B版本号Bxxx")

    return df