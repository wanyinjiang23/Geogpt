from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from georetail.data import export_data

if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../过程文件/GeoRetail_20261109/demo_data")
    export_data(root)
    print(root.resolve())
