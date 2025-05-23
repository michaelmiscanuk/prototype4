import requests
import pandas as pd
from pyjstat import pyjstat
import os
import time
from pathlib import Path
from tqdm import tqdm
import json

# Create data/CSVs directory if it doesn't exist
csv_dir = Path("data/CSVs")
csv_dir.mkdir(parents=True, exist_ok=True)

# Configuration
PROCESS_ALL_DATASETS = 1  # Set to 1 to process all datasets, 0 to process specific dataset
SPECIFIC_DATASET_ID = "OBY01PD"  # Only used when PROCESS_ALL_DATASETS is 0
PROCESS_ALL_SELECTIONS = 1  # Set to 1 to process all selections, 0 to process specific selection
SPECIFIC_SELECTION_ID = "OBY01PDT01"  # Only used when PROCESS_ALL_SELECTIONS is 0

def fetch_json(url):
    """Helper function to fetch JSON data with error handling and rate limiting"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        time.sleep(0.1)  # Rate limiting to be nice to the API
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def save_to_csv(df, filename):
    """Helper function to save DataFrame to CSV"""
    try:
        output_path = csv_dir / filename
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"Saved: {filename} to {output_path}")
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False

def main():
    # Print configuration
    if PROCESS_ALL_DATASETS:
        print("Processing all available datasets")
    else:
        print(f"Processing only dataset: {SPECIFIC_DATASET_ID}")
        
    if PROCESS_ALL_SELECTIONS:
        print("Processing all available selections")
    else:
        print(f"Processing only selection: {SPECIFIC_SELECTION_ID}")

    # 1. Get list of all datasets
    print("Fetching list of datasets...")
    datasets_url = "https://data.csu.gov.cz/api/katalog/v1/sady"
    datasets = fetch_json(datasets_url)
    
    if not datasets:
        print("Failed to fetch datasets list")
        return

    print(f"\nFound {len(datasets)} datasets to process")
    successful_saves = 0
    failed_datasets = []
    failed_selections = []

    # Process each dataset with progress bar
    for dataset in tqdm(datasets, desc="Processing datasets", unit="dataset"):
        dataset_id = dataset.get('kod')  # Using 'kod' instead of 'id'
        if not dataset_id:
            print(f"Warning: Could not find kod in dataset: {dataset}")
            continue
            
        # Skip if not processing all datasets and this isn't the specific dataset
        if not PROCESS_ALL_DATASETS and dataset_id != SPECIFIC_DATASET_ID:
            continue

        # 2. Get dataset details
        dataset_url = f"https://data.csu.gov.cz/api/katalog/v1/sady/{dataset_id}"
        dataset_details = fetch_json(dataset_url)
        
        if not dataset_details:
            failed_datasets.append(dataset_id)
            continue

        # 3. Get available selections for this dataset
        selections_url = f"https://data.csu.gov.cz/api/katalog/v1/sady/{dataset_id}/vybery"
        selections = fetch_json(selections_url)
        
        if not selections:
            failed_datasets.append(dataset_id)
            continue

        # 4. Process each selection with nested progress bar
        for selection in tqdm(selections, desc=f"Processing selections for {dataset_id}", 
                            leave=False, unit="selection"):
            selection_id = selection.get('kod')  # Using 'kod' instead of 'id'
            if not selection_id:
                print(f"Warning: Could not find kod in selection: {selection}")
                continue
            
            # Skip if not processing all selections and this isn't the specific selection
            if not PROCESS_ALL_SELECTIONS and selection_id != SPECIFIC_SELECTION_ID:
                continue
            
            # Fetch the actual data
            data_url = f"https://data.csu.gov.cz/api/dotaz/v1/data/vybery/{selection_id}"
            data = fetch_json(data_url)
            
            if not data:
                failed_selections.append(selection_id)
                continue

            try:
                # Convert JSON-stat to pandas DataFrame - using the same approach as data2.py
                df = pyjstat.from_json_stat(data)[0]
                
                if df.empty:
                    print(f"Warning: Empty DataFrame for {selection_id}")
                    failed_selections.append(selection_id)
                    continue
                
                # Generate filename
                filename = f"{selection_id}.csv"
                
                # Save to CSV
                if save_to_csv(df, filename):
                    successful_saves += 1
                else:
                    failed_selections.append(selection_id)
                
            except Exception as e:
                print(f"Error processing {selection_id}: {e}")
                failed_selections.append(selection_id)

    print(f"\nProcessing complete:")
    print(f"Successfully saved {successful_saves} files to {csv_dir}")
    if failed_datasets:
        print(f"\nFailed to process {len(failed_datasets)} datasets:")
        print(json.dumps(failed_datasets, indent=2))
    if failed_selections:
        print(f"\nFailed to process {len(failed_selections)} selections:")
        print(json.dumps(failed_selections, indent=2))

if __name__ == "__main__":
    main() 