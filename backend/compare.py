import os
import pandas as pd
import re


csv_path = "/Users/ry/capstone-project-25t3-9900-f18a-donut/capstone-project-25t3-9900-f18a-donut/data/dimension_sub/subthemes_with_dim.csv"
json_dir = "/Users/ry/capstone-project-25t3-9900-f18a-donut/capstone-project-25t3-9900-f18a-donut/backend/subthemes_sr/"


df = pd.read_csv(csv_path)


def to_filename(subtheme):
    name = str(subtheme).lower()
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return f"subtheme_{name}.json"

csv_files = set(df["subthemes"].apply(to_filename))


json_files = set(f for f in os.listdir(json_dir) if f.endswith(".json"))


extra_in_json = sorted(json_files - csv_files)
missing_in_json = sorted(csv_files - json_files)





with open("extra_in_json.txt", "w") as f:
    f.write("\n".join(extra_in_json))
with open("missing_json.txt", "w") as f:
    f.write("\n".join(missing_in_json))

