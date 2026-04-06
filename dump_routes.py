import sys

FILE_PATH = "routes/payroll.py"

with open(FILE_PATH, "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith("@payroll_bp"):
        # Check next few lines for decorators
        route = line.strip()
        decorators = [lines[i+x].strip() for x in range(1, 4) if lines[i+x].startswith("@")]
        print(f"{route}")
        for d in decorators:
            print(f"  {d}")

