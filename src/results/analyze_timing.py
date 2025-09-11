#!/usr/bin/env python3
"""
Script to analyze timing information from ipack server logs.
Extracts lines containing "took X seconds" and provides runtime efficiency analysis.
"""

import re
import statistics
from collections import defaultdict
from pathlib import Path

def extract_timing_data(log_file_path):
    """Extract timing information from log file."""
    timing_pattern = r'(.+?)\s+took\s+([\d.]+)\s+seconds'
    timing_data = []
    
    with open(log_file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            match = re.search(timing_pattern, line)
            if match:
                function_name = match.group(1).strip()
                duration = float(match.group(2))
                timing_data.append({
                    'line_num': line_num,
                    'function': function_name,
                    'duration': duration,
                    'raw_line': line.strip()
                })
    
    return timing_data

def analyze_timing_data(timing_data):
    """Analyze timing data and generate statistics."""
    if not timing_data:
        return "No timing data found in the log file."
    
    # Group by function name
    function_stats = defaultdict(list)
    for entry in timing_data:
        function_stats[entry['function']].append(entry['duration'])
    
    analysis = []
    analysis.append("=== TIMING ANALYSIS REPORT ===\n")
    
    # Overall statistics
    all_durations = [entry['duration'] for entry in timing_data]
    total_time = sum(all_durations)
    analysis.append(f"Total execution time: {total_time:.3f} seconds")
    analysis.append(f"Number of timed operations: {len(timing_data)}")
    analysis.append(f"Average operation time: {statistics.mean(all_durations):.3f} seconds")
    analysis.append(f"Median operation time: {statistics.median(all_durations):.3f} seconds")
    analysis.append(f"Min operation time: {min(all_durations):.3f} seconds")
    analysis.append(f"Max operation time: {max(all_durations):.3f} seconds")
    if len(all_durations) > 1:
        analysis.append(f"Standard deviation: {statistics.stdev(all_durations):.3f} seconds")
    analysis.append("")
    
    # Function-specific statistics
    analysis.append("=== FUNCTION-SPECIFIC ANALYSIS ===\n")
    
    for function_name, durations in sorted(function_stats.items()):
        analysis.append(f"Function: {function_name}")
        analysis.append(f"  Calls: {len(durations)}")
        analysis.append(f"  Total time: {sum(durations):.3f} seconds")
        analysis.append(f"  Average time: {statistics.mean(durations):.3f} seconds")
        analysis.append(f"  Min time: {min(durations):.3f} seconds")
        analysis.append(f"  Max time: {max(durations):.3f} seconds")
        if len(durations) > 1:
            analysis.append(f"  Std deviation: {statistics.stdev(durations):.3f} seconds")
        
        # Performance insights
        avg_time = statistics.mean(durations)
        if avg_time > 0.5:
            analysis.append(f"  ⚠️  HIGH LATENCY: Average > 0.5s")
        elif avg_time > 0.2:
            analysis.append(f"  ⚡ MODERATE LATENCY: Average > 0.2s")
        else:
            analysis.append(f"  ✅ LOW LATENCY: Average < 0.2s")
        
        analysis.append("")
    
    # Performance ranking
    analysis.append("=== PERFORMANCE RANKING (by total time) ===\n")
    function_totals = [(func, sum(durations)) for func, durations in function_stats.items()]
    function_totals.sort(key=lambda x: x[1], reverse=True)
    
    for i, (function_name, total_time) in enumerate(function_totals, 1):
        calls = len(function_stats[function_name])
        avg_time = total_time / calls
        analysis.append(f"{i:2d}. {function_name:<40} "
                       f"Total: {total_time:6.3f}s "
                       f"Calls: {calls:3d} "
                       f"Avg: {avg_time:6.3f}s")
    
    analysis.append("")
    
    # Raw timing data
    analysis.append("=== RAW TIMING DATA ===\n")
    for entry in timing_data:
        analysis.append(f"Line {entry['line_num']:3d}: {entry['function']:<40} "
                       f"{entry['duration']:8.3f}s")
    
    return '\n'.join(analysis)

def main():
    """Main function to run the timing analysis."""
    # log_file = Path("ipack/serverlog.txt")
    log_file = Path("ipack/serverlog2.txt")
    
    if not log_file.exists():
        print(f"Error: Log file '{log_file}' not found!")
        return
    
    print(f"Analyzing timing data from: {log_file}")
    print("-" * 50)
    
    timing_data = extract_timing_data(log_file)
    analysis_report = analyze_timing_data(timing_data)
    
    print(analysis_report)
    
    # Also save to file
    # output_file = Path("timing_analysis_report.txt")
    output_file = Path("timing_analysis_report2.txt")
    with open(output_file, 'w') as f:
        f.write(analysis_report)
    
    print(f"\nDetailed report saved to: {output_file}")

if __name__ == "__main__":
    main() 