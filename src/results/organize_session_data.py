import os
import json
import shutil
import argparse
import re
import datetime
from collections import defaultdict

def organize_session_data(participant_id):
    """
    Organize session data for a participant.
    
    This script:
    1. Reads ALL log files from ipack/api/logs
    2. Extracts session_ids from them
    3. Groups logs by session_id
    4. Finds corresponding results folders (using first 10 chars of session_id)
    5. Copies both to userstudy/<participant>/<index>_<session_id[:10]>_<task>_<attempt> directories
    
    Note: This assumes all current log files in api/logs belong to the specified participant.
    """
    # Create userstudy directory if it doesn't exist
    if not os.path.exists("userstudy"):
        os.makedirs("userstudy")
        print("Created userstudy directory")
        
    # Create base directory for the participant if it doesn't exist
    participant_dir = os.path.join("userstudy", participant_id)
    os.makedirs(participant_dir, exist_ok=True)
    
    # Paths to source directories
    logs_dir = os.path.join("ipack", "api", "logs")
    pickle_dir = os.path.join("ipack", "api", "pickle_store")
    results_dir = os.path.join("ipack", "api", "results")
    
    # Dictionary to track session_ids and their associated log files
    session_logs = defaultdict(list)
    session_timestamps = {}
    session_tasks = {}
    
    # Process log files to extract session_ids
    log_files = [f for f in os.listdir(logs_dir) if f.endswith('.json')]
    
    for log_file in log_files:
        log_path = os.path.join(logs_dir, log_file)
        
        try:
            with open(log_path, 'r') as f:
                log_data = json.load(f)
                
            # Extract session_id if it exists
            if 'session_id' in log_data:
                session_id = log_data['session_id']
                session_logs[session_id].append(log_file)
                
                # Extract timestamp from the filename
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', log_file)
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                    # Store the earliest timestamp for each session
                    if session_id not in session_timestamps or timestamp_str < session_timestamps[session_id]:
                        session_timestamps[session_id] = timestamp_str
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error processing {log_file}: {e}")
    
    # Determine task type by reading the last log file for each session
    for session_id, files in session_logs.items():
        # Sort log files by timestamp to get the last one
        sorted_logs = sorted(files, key=lambda f: f)
        if sorted_logs:
            last_log = sorted_logs[-1]
            last_log_path = os.path.join(logs_dir, last_log)
            
            try:
                with open(last_log_path, 'r') as f:
                    log_data = json.load(f)
                
                # Check if we can find fabric folder information
                if 'fabric_folder' in log_data:
                    fabric_folder = log_data['fabric_folder']
                    # Determine task based on fabric folder
                    if "ui_test2" in fabric_folder:
                        session_tasks[session_id] = "tutorial"
                    elif "linen_pp_resized" in fabric_folder:
                        session_tasks[session_id] = "task1"
                    elif "studyset_resized" in fabric_folder:
                        session_tasks[session_id] = "task2"
                    else:
                        session_tasks[session_id] = "unknown"
                else:
                    # If fabric_folder isn't directly in the log, look for it in other fields
                    task_type = "unknown"
                    
                    # Try to find fabric folder info in action data or other fields
                    # This is a fallback approach that checks various possible locations
                    json_str = json.dumps(log_data)
                    if "ui_test2" in json_str:
                        task_type = "tutorial"
                    elif "linen_pp_resized" in json_str:
                        task_type = "task1"
                    elif "studyset_resized" in json_str:
                        task_type = "task2"
                    
                    session_tasks[session_id] = task_type
            except Exception as e:
                print(f"Error determining task type from log {last_log}: {e}")
                session_tasks[session_id] = "unknown"
    
    # Sort sessions chronologically based on their earliest timestamp
    sorted_sessions = sorted(session_logs.keys(), 
                            key=lambda sid: session_timestamps.get(sid, "9999-99-99_99-99-99"))
    
    # Process each unique session
    for index, session_id in enumerate(sorted_sessions, 1):
        log_files = session_logs[session_id]
        results_folder_name = session_id[:10]
        results_folder_path = os.path.join(results_dir, results_folder_name)
        
        # Get task type from the session_tasks dictionary
        task_type = session_tasks.get(session_id, "unknown")
        attempt_num = 1  # Default attempt number
        
        # Check if there's a current_session.pkl to determine if this is a completed session
        has_current_session = False
        if os.path.exists(results_folder_path) and os.path.isdir(results_folder_path):
            for root, dirs, files in os.walk(results_folder_path):
                if "current_session.pkl" in files:
                    has_current_session = True
                    break
            
            result_type = "result" if has_current_session else "attempt"
        else:
            result_type = "attempt"  # No results folder, treat as attempt
        
        # Create a more descriptive folder name
        folder_name = f"{index:02d}_{results_folder_name}_{task_type}_{result_type}"
        
        # Update folder with counting if needed (for multiple attempts)
        existing_similar_folders = [f for f in os.listdir(participant_dir) 
                                   if f.startswith(f"{index:02d}_{results_folder_name}_{task_type}_{result_type}")]
        if existing_similar_folders:
            attempt_num = len(existing_similar_folders) + 1
            folder_name = f"{index:02d}_{results_folder_name}_{task_type}_{result_type}{attempt_num}"
        
        # Create session directory with new naming
        session_dir = os.path.join(participant_dir, folder_name)
        logs_session_dir = os.path.join(session_dir, "logs")
        pickle_session_dir = os.path.join(session_dir, "pickle_store")
        results_session_dir = os.path.join(session_dir, "results")
        
        os.makedirs(logs_session_dir, exist_ok=True)
        os.makedirs(pickle_session_dir, exist_ok=True)
        
        # Copy log files
        for log_file in log_files:
            src_path = os.path.join(logs_dir, log_file)
            dst_path = os.path.join(logs_session_dir, log_file)
            shutil.copy2(src_path, dst_path)
        
        # Check if corresponding results directory exists (first 10 chars of session_id)
        if os.path.exists(results_folder_path) and os.path.isdir(results_folder_path):
            os.makedirs(results_session_dir, exist_ok=True)
            # Copy entire results directory
            for item in os.listdir(results_folder_path):
                src_item = os.path.join(results_folder_path, item)
                dst_item = os.path.join(results_session_dir, item)
                
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_item, dst_item)
            
            print(f"Copied session {session_id} data to {session_dir}")
        else:
            print(f"No results folder found for session {session_id} (looked for {results_folder_name})")
        
        # Check if corresponding bin pickle file exists
        bin_pickle_file = os.path.join(pickle_dir, f"{session_id}.pkl")
        target_bin_pickle_file = os.path.join(pickle_session_dir, f"{session_id[:10]}_bins.pkl")
        if os.path.exists(bin_pickle_file):
            shutil.copy2(bin_pickle_file, target_bin_pickle_file)
            print(f"Copied bin pickle file for session {session_id} to {pickle_session_dir}")
        else:
            print(f"No bin pickle file found for session {session_id}")
    
    print(f"Organized {len(session_logs)} sessions for participant {participant_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize session data by participant ID")
    parser.add_argument("participant_id", help="ID of the participant")
    
    args = parser.parse_args()
    organize_session_data(args.participant_id) 

# Usage:
# python scripts/organize_session_data.py <participant id, such as P01>