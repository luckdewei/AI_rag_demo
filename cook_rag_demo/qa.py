from pathlib import Path


data_path: str = "./cook"


data_path_obj = Path(data_path)

print(f"resolve path:  {Path(data_path).resolve()}")
data_root = Path(data_path).resolve()

for md_file in data_path_obj.rglob("*.md"):
    # print(f"md_file: {md_file}")
    relative_path = Path(md_file).resolve().relative_to(data_root).as_posix()
    print(f"relative_path:{relative_path}")
    # pass
