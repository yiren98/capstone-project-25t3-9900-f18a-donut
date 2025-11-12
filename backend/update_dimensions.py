import pandas as pd
import json
import os
import re

csv_path = "/Users/ry/capstone-project-25t3-9900-f18a-donut/capstone-project-25t3-9900-f18a-donut/data/dimension_sub/subthemes_with_dim.csv"
json_dir = "/Users/ry/capstone-project-25t3-9900-f18a-donut/capstone-project-25t3-9900-f18a-donut/backend/subthemes_sr/"
output_path = "/Users/ry/capstone-project-25t3-9900-f18a-donut/capstone-project-25t3-9900-f18a-donut/data/dimension_sub/subthemes_with_dim_update.csv"

df = pd.read_csv(csv_path)

def to_filename(subtheme):
    if pd.isna(subtheme):
        return ""
    name = subtheme.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return f"subtheme_{name}.json"

df["mapped_file"] = df["subthemes"].apply(to_filename)

def get_dimensions_from_json(filename):
    path = os.path.join(json_dir, filename)
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "parent_dimensions" in data:
                return "; ".join(data["parent_dimensions"])
    except Exception as e:
        print(f" read {filename} file: {e}")
    return ""

df["mapped_dimension"] = df["mapped_file"].apply(get_dimensions_from_json)

df.to_csv(output_path, index=False, encoding="utf-8")
print(f"output：{output_path}")
