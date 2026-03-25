"""
Complete Apple Health export.xml -> CSV converter.
Extracts ALL data elements including nested HRV beats, workout events/stats,
correlations, and personal info.

Usage (from project root):
    uv run python scripts/export_csv.py raw/导出.xml --out output
"""
import json
import os
import sys
import time
import xml.etree.ElementTree as ET

import pandas as pd


def metadata_dict(elem):
    """Extract MetadataEntry children as a flat dict."""
    out = {}
    for m in elem.findall('.//MetadataEntry'):
        k = m.get('key')
        v = m.get('value')
        if k:
            out[f"metadata:{k}"] = v
    return out


def extract_hrv_beats(elem):
    """Extract InstantaneousBeatsPerMinute from a HeartRateVariabilityMetadataList."""
    beats = []
    for ibpm in elem.findall('.//InstantaneousBeatsPerMinute'):
        beats.append({
            'bpm': ibpm.get('bpm'),
            'time': ibpm.get('time'),
        })
    return beats


def iterparse_export_full(file_path):
    """
    Full iterative parsing of export.xml with nested element extraction.
    Returns a dict of all element lists.
    """
    records = []
    workouts = []
    activities = []
    correlations = []
    hrv_beats = []  # Flattened: each row = one beat with parent record ref
    workout_events = []
    workout_statistics = []
    workout_routes = []
    me_info = {}

    print(f"Parsing {file_path} ...")
    t0 = time.time()
    count = 0

    # We need to handle nested elements, so we use a context approach
    # iterparse with 'start' and 'end' to track parent context
    context_stack = []

    for event, elem in ET.iterparse(file_path, events=('start', 'end')):
        if event == 'start':
            context_stack.append(elem.tag)
            continue

        # event == 'end'
        tag = elem.tag
        if context_stack:
            context_stack.pop()

        if tag == 'Me':
            me_info = dict(elem.attrib)
            count += 1

        elif tag == 'Record':
            row = dict(elem.attrib)
            row.update(metadata_dict(elem))

            # Check if this record has HRV metadata list
            hrv_list = elem.find('HeartRateVariabilityMetadataList')
            if hrv_list is not None:
                record_start = row.get('startDate', '')
                record_end = row.get('endDate', '')
                for ibpm in hrv_list.findall('InstantaneousBeatsPerMinute'):
                    hrv_beats.append({
                        'recordStartDate': record_start,
                        'recordEndDate': record_end,
                        'bpm': ibpm.get('bpm'),
                        'time': ibpm.get('time'),
                    })

            records.append(row)
            count += 1
            elem.clear()

        elif tag == 'Workout':
            row = dict(elem.attrib)
            row.update(metadata_dict(elem))

            # Extract nested WorkoutEvent
            for we in elem.findall('WorkoutEvent'):
                we_row = dict(we.attrib)
                we_row['workoutStartDate'] = row.get('startDate', '')
                we_row['workoutActivityType'] = row.get('workoutActivityType', '')
                workout_events.append(we_row)

            # Extract nested WorkoutStatistics
            for ws in elem.findall('WorkoutStatistics'):
                ws_row = dict(ws.attrib)
                ws_row['workoutStartDate'] = row.get('startDate', '')
                ws_row['workoutActivityType'] = row.get('workoutActivityType', '')
                workout_statistics.append(ws_row)

            # Extract nested WorkoutRoute -> FileReference
            for wr in elem.findall('WorkoutRoute'):
                wr_row = dict(wr.attrib)
                fr = wr.find('FileReference')
                if fr is not None:
                    wr_row['filePath'] = fr.get('path', '')
                wr_row['workoutStartDate'] = row.get('startDate', '')
                wr_row['workoutActivityType'] = row.get('workoutActivityType', '')
                workout_routes.append(wr_row)

            workouts.append(row)
            count += 1
            elem.clear()

        elif tag == 'ActivitySummary':
            row = dict(elem.attrib)
            activities.append(row)
            count += 1
            elem.clear()

        elif tag == 'Correlation':
            row = dict(elem.attrib)
            row.update(metadata_dict(elem))
            # Extract nested Records inside Correlation
            nested_records = []
            for nr in elem.findall('Record'):
                nested_records.append(dict(nr.attrib))
            if nested_records:
                row['nested_records_count'] = len(nested_records)
                # Flatten: store nested record types
                row['nested_types'] = ';'.join(
                    nr.get('type', '') for nr in elem.findall('Record')
                )
                # Store nested values
                for i, nr in enumerate(elem.findall('Record')):
                    nr_attrs = dict(nr.attrib)
                    for k, v in nr_attrs.items():
                        row[f'nested_{i}_{k}'] = v
            correlations.append(row)
            count += 1
            elem.clear()

        if count % 500000 == 0 and count > 0:
            elapsed = time.time() - t0
            print(f"  ...processed {count:,} elements ({elapsed:.1f}s)")

    elapsed = time.time() - t0
    print(f"Parsing complete in {elapsed:.1f}s - {count:,} total elements")

    return {
        'records': records,
        'workouts': workouts,
        'activity_summaries': activities,
        'correlations': correlations,
        'hrv_beats': hrv_beats,
        'workout_events': workout_events,
        'workout_statistics': workout_statistics,
        'workout_routes': workout_routes,
        'me_info': me_info,
    }


def write_csv(rows, out_path, label=None):
    """Write list of dicts to CSV via pandas."""
    label = label or os.path.basename(out_path)
    if not rows:
        print(f"  {label}: (no data)")
        return
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"  {label}: {len(df):,} rows, {size_mb:.1f} MB")


def main():
    if len(sys.argv) < 2:
        print("Usage: python export_csv.py <export.xml> [--out <output_dir>]")
        sys.exit(1)

    xml_path = sys.argv[1]
    out_dir = '.'
    if '--out' in sys.argv:
        idx = sys.argv.index('--out')
        if idx + 1 < len(sys.argv):
            out_dir = sys.argv[idx + 1]

    if not os.path.isfile(xml_path):
        print(f"Error: file not found: {xml_path}")
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)

    data = iterparse_export_full(xml_path)

    print(f"\nWriting outputs to {os.path.abspath(out_dir)}/")
    print("=" * 50)

    # Core data
    write_csv(data['records'], os.path.join(out_dir, 'records.csv'), 'records.csv')
    write_csv(data['workouts'], os.path.join(out_dir, 'workouts.csv'), 'workouts.csv')
    write_csv(data['activity_summaries'], os.path.join(out_dir, 'activity_summary.csv'), 'activity_summary.csv')

    # Extended data
    write_csv(data['correlations'], os.path.join(out_dir, 'correlations.csv'), 'correlations.csv')
    write_csv(data['hrv_beats'], os.path.join(out_dir, 'hrv_beats.csv'), 'hrv_beats.csv')
    write_csv(data['workout_events'], os.path.join(out_dir, 'workout_events.csv'), 'workout_events.csv')
    write_csv(data['workout_statistics'], os.path.join(out_dir, 'workout_statistics.csv'), 'workout_statistics.csv')
    write_csv(data['workout_routes'], os.path.join(out_dir, 'workout_routes.csv'), 'workout_routes.csv')

    # Personal info as JSON
    if data['me_info']:
        me_path = os.path.join(out_dir, 'me.json')
        with open(me_path, 'w', encoding='utf-8') as f:
            json.dump(data['me_info'], f, ensure_ascii=False, indent=2)
        print(f"  me.json: personal info saved")

    # Print summary
    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  Records:             {len(data['records']):>10,}")
    print(f"  Workouts:            {len(data['workouts']):>10,}")
    print(f"  Activity Summaries:  {len(data['activity_summaries']):>10,}")
    print(f"  Correlations:        {len(data['correlations']):>10,}")
    print(f"  HRV Beats:           {len(data['hrv_beats']):>10,}")
    print(f"  Workout Events:      {len(data['workout_events']):>10,}")
    print(f"  Workout Statistics:  {len(data['workout_statistics']):>10,}")
    print(f"  Workout Routes:      {len(data['workout_routes']):>10,}")

    # Also list all unique record types found
    type_counts = {}
    for r in data['records']:
        t = r.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"\n  Unique record types: {len(type_counts)}")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        short = t.replace('HKQuantityTypeIdentifier', '').replace('HKCategoryTypeIdentifier', 'Cat:').replace('HKDataType', 'Data:')
        print(f"    {c:>10,}  {short}")


if __name__ == '__main__':
    main()
