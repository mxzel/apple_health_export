# Apple Health Data Export & Analysis

# Default: show available recipes
default:
    @just --list

# Parse raw XML into CSVs in output/
export:
    uv run python scripts/export_csv.py raw/export.xml --out output

# Show record type summary from existing output
summary:
    @uv run python -c "\
    import pandas as pd; \
    r = pd.read_csv('output/records.csv', usecols=['type'], low_memory=False); \
    tc = r['type'].value_counts(); \
    print(f'Total records: {len(r):,}  |  Unique types: {len(tc)}'); \
    print(); \
    [print(f'  {c:>10,}  {t.split(\"Identifier\")[-1]}') for t, c in tc.items()]"

# Show workout summary
workouts:
    @uv run python -c "\
    import pandas as pd; \
    w = pd.read_csv('output/workouts.csv'); \
    print(f'Total workouts: {len(w)}'); \
    print(); \
    tc = w['workoutActivityType'].value_counts(); \
    [print(f'  {c:>5}  {t.replace(\"HKWorkoutActivityType\", \"\")}') for t, c in tc.items()]"

# Clean generated output
clean:
    rm -rf output/*
