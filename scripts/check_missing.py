import os
import re

PATTERN = re.compile(r"^(\d{4})-(\d{5})$")  # e.g. 2303-07856

def collect_ids(base_dir: str):
    ids = []
    for entry in os.scandir(base_dir):
        if entry.is_dir():
            m = PATTERN.match(entry.name)
            if m:
                yymm = m.group(1)
                tail = m.group(2)
                ids.append((entry.name, yymm, int(tail)))
    return sorted(ids, key=lambda x: x[2])  # sort by numeric tail

def check_sequence(base_dir: str, start_tail: int = 7856, end_tail: int = 9100):
    ids = collect_ids(base_dir)
    if not ids:
        print("No matching folders.")
        return

    print(f"Found {len(ids)} candidate folders.")
    tails = [t for _, _, t in ids]

    # Check ordering
    is_strict_increasing = all(tails[i] < tails[i+1] for i in range(len(tails)-1))
    print(f"Strictly increasing: {is_strict_increasing}")

    # Expected range
    expected_set = set(range(start_tail, end_tail + 1))
    present_set = set(tails)
    missing = sorted(expected_set - present_set)
    extra = sorted(present_set - expected_set)

    print(f"Start expected: {start_tail}, End expected: {end_tail}")
    print(f"Present min: {min(tails)}, Present max: {max(tails)}")

    if missing:
        print(f"Missing ({len(missing)}): {', '.join(f'"{m:05d}"' for m in missing[:50])}"
              + (" ..." if len(missing) > 50 else ""))
    else:
        print("No missing IDs in range.")

    if extra:
        print(f"Out-of-range ({len(extra)}): {', '.join(f'{e:05d}' for e in extra[:50])}"
              + (" ..." if len(extra) > 50 else ""))
    else:
        print("No out-of-range IDs.")

    # List first and last few folders
    print("First 5 folders:")
    for name, yymm, tail in ids[:5]:
        print(f"  {name} (tail={tail})")
    print("Last 5 folders:")
    for name, yymm, tail in ids[-5:]:
        print(f"  {name} (tail={tail})")

if __name__ == "__main__":
    BASE_DIR = r"d:\Data\Learning\University\Year3\Intro to DS\Data_Science_Project\Milestone1\23127130"
    check_sequence(BASE_DIR, start_tail=7856, end_tail=12855)