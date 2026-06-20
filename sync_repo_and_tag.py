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