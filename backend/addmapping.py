import os
import pandas as pd
import re

input_path = "/Users/ry/capstone-project-25t3-9900-f18a-donut/capstone-project-25t3-9900-f18a-donut/data/dimension_sub/subthemes_with_dim.csv"
json_dir = "/Users/ry/capstone-project-25t3-9900-f18a-donut/capstone-project-25t3-9900-f18a-donut/backend/subthemes_sr/"
output_path = "/Users/ry/capstone-project-25t3-9900-f18a-donut/capstone-project-25t3-9900-f18a-donut/data/dimension_sub/subthemes_with_dim_addmap.csv"

df = pd.read_csv(input_path)

def to_filename(subtheme):
    if pd.isna(subtheme):
        return ""
    name = subtheme.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return f"subtheme_{name}.json"

df["mapped_file"] = df["subthemes"].apply(to_filename)
df["file_exists"] = df["mapped_file"].apply(lambda f: os.path.exists(os.path.join(json_dir, f)))

df.to_csv(output_path, index=False, encoding="utf-8")
print(f"✅ save to：{output_path}")
