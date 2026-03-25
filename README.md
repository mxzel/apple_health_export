# 🍎 Apple Health Export Parser

Fast, lightweight parser for Apple Health data exports. Converts the raw `export.xml` (~1-2GB) into clean, analysis-ready CSV files in under 60 seconds.

**No AI dependencies. No GUI. Just your data.**

## Features

- ⚡ **Fast** — streams 1.8GB XML in ~58s via `iterparse`, no full DOM load
- 📦 **Complete** — extracts **all** data types (52+ record types), not just basics
- 🫀 **HRV Beat-level Data** — extracts every instantaneous beat-to-beat measurement
- 🏋️ **Full Workout Detail** — events, statistics, GPS route references
- 🪶 **Minimal Dependencies** — only `pandas` + `matplotlib`, managed by `uv`

## Quick Start

### 1. Export your Apple Health data

On your iPhone: **Health App → Profile → Export All Health Data** → transfer the zip to your Mac and unzip.

### 2. Clone & run

```bash
git clone https://github.com/YOUR_USERNAME/apple-health-export.git
cd apple-health-export

# Place your export XML in raw/
cp /path/to/export.xml raw/    # or raw/export.xml

# Parse everything
just export
# or manually:
uv run python scripts/export_csv.py raw/导出.xml --out output
```

> **Prerequisites**: [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just) (optional). No other setup needed — `uv` handles the virtualenv and dependencies automatically.

## Output Files

All parsed data lands in `output/`:

| File | Description | Example Size |
|------|-------------|-------------|
| `records.csv` | All health records (52+ types) | ~1.4 GB |
| `hrv_beats.csv` | Beat-to-beat HRV data | ~44 MB |
| `workouts.csv` | Workout sessions | ~0.2 MB |
| `workout_events.csv` | Pause/resume/lap events | ~0.6 MB |
| `workout_statistics.csv` | Per-workout stats (HR, calories, etc.) | ~0.4 MB |
| `workout_routes.csv` | GPS route file references | ~0.1 MB |
| `activity_summary.csv` | Daily activity ring data | ~0.1 MB |
| `correlations.csv` | Correlated measurements (e.g. blood pressure) | ~0.0 MB |
| `me.json` | Personal info (birthday, sex, blood type) | tiny |

## Extracted Record Types

<details>
<summary>Full list of 52+ health record types</summary>

**Cardiac**: HeartRate, HeartRateVariabilitySDNN, RestingHeartRate, WalkingHeartRateAverage, HeartRateRecoveryOneMinute

**Activity**: StepCount, ActiveEnergyBurned, BasalEnergyBurned, AppleExerciseTime, AppleStandTime, FlightsClimbed, PhysicalEffort

**Movement**: DistanceWalkingRunning, DistanceCycling, WalkingSpeed, WalkingStepLength, StairAscentSpeed, StairDescentSpeed

**Running Dynamics**: RunningPower, RunningSpeed, RunningStrideLength, RunningVerticalOscillation, RunningGroundContactTime

**Gait Analysis**: WalkingDoubleSupportPercentage, WalkingAsymmetryPercentage, AppleWalkingSteadiness

**Respiratory**: RespiratoryRate, OxygenSaturation, AppleSleepingBreathingDisturbances

**Sleep**: SleepAnalysis, AppleSleepingWristTemperature

**Body Measurements**: BodyMass, Height, BloodPressureSystolic, BloodPressureDiastolic

**Fitness**: VO2Max, SixMinuteWalkTestDistance

**Environment**: EnvironmentalAudioExposure, HeadphoneAudioExposure, TimeInDaylight

**Nutrition**: DietaryWater, DietaryProtein, DietaryCarbohydrates, DietaryFatTotal

**Other**: HandwashingEvent, MindfulSession, AudioExposureEvent, HighHeartRateEvent, LowCardioFitnessEvent
</details>

## Project Structure

```
apple-health-export/
├── raw/                    # Your exported health data (gitignored)
│   ├── export.xml          # Main Apple Health export
│   ├── electrocardiograms/ # ECG recordings
│   └── workout-routes/     # GPX files
├── output/                 # Parsed CSVs (gitignored, regenerable)
├── scripts/
│   └── export_csv.py       # The parser
├── justfile                # Task runner recipes
└── pyproject.toml          # Python project config
```

## Justfile Recipes

```bash
just            # Show available recipes
just export     # Parse XML → CSVs
just summary    # Show record type breakdown
just workouts   # Show workout type breakdown
just clean      # Delete generated output
```

## How It Works

The parser uses Python's `xml.etree.ElementTree.iterparse` to stream through the XML without loading it all into memory. It extracts:

1. **Records** — every `<Record>` element with all attributes and metadata
2. **HRV Beats** — nested `<InstantaneousBeatsPerMinute>` inside HRV records
3. **Workouts** — `<Workout>` elements plus nested events, statistics, and route references
4. **Activity Summaries** — daily `<ActivitySummary>` (Move/Exercise/Stand rings)
5. **Correlations** — `<Correlation>` elements (e.g., blood pressure pairs)
6. **Personal Info** — `<Me>` element (saved as JSON)

## FAQ

**Q: Why not use the [krumjahn/applehealth](https://github.com/krumjahn/applehealth) repo?**
It requires `openai`, `anthropic`, `ollama`, `PyQt6`, and other heavy AI/GUI dependencies just to parse XML. This tool does the same data extraction with only `pandas`.

**Q: What about ECG data?**
ECG recordings are exported as separate CSV files in `raw/electrocardiograms/`, not embedded in the XML. They're already in a usable format.

**Q: Can I use this with pandas directly?**
Yes! After running the export:
```python
import pandas as pd
df = pd.read_csv('output/records.csv', low_memory=False)
hr = df[df['type'] == 'HKQuantityTypeIdentifierHeartRate']
```

## License

MIT
