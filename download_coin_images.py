#!/usr/bin/env python3
"""
Download coin images from URLs and store locally.
Updates coins_seed.csv with local file paths.
"""

import csv
import os
import requests
from pathlib import Path
from urllib.parse import urlparse

OUTPUT_DIR = Path("/Users/jacktabb/Desktop/app/public/images/coins")
CSV_FILE = Path("/Users/jacktabb/Desktop/app/data/coins_seed.csv")

def download_image(url, coin_id):
    """
    Download image from URL and save locally.
    Returns the local path relative to public folder, or empty string on failure.
    """
    if not url:
        return ""
    
    try:
        # Create output directory if needed
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Get file extension from URL
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1] or ".png"
        
        # Save as coin_id.ext
        filename = f"{coin_id}{ext}"
        filepath = OUTPUT_DIR / filename
        
        # Download
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Save
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        # Return relative path for database storage
        # This assumes your frontend serves from /public/images/coins/
        return f"/images/coins/{filename}"
    
    except Exception as e:
        print(f"  ✗ Failed to download {coin_id}: {e}")
        return ""

def download_all_images():
    """
    Read CSV, download all images, update CSV with local paths.
    """
    rows = []
    
    with open(CSV_FILE, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Downloading {len(rows)} coin images...")
    
    for i, row in enumerate(rows):
        coin_id = row['id']
        url = row['image_url']
        
        if url and url.startswith('http'):
            print(f"[{i+1}/{len(rows)}] {coin_id:25s}", end=' ', flush=True)
            local_path = download_image(url, coin_id)
            
            if local_path:
                row['image_url'] = local_path  # Replace URL with local path
                print(f"✓ -> {local_path}")
            else:
                print("✗")
        else:
            print(f"[{i+1}/{len(rows)}] {coin_id:25s} (no URL or already local)")
    
    # Write updated CSV
    with open(CSV_FILE, 'w', newline='') as f:
        fieldnames = ['id', 'symbol', 'name', 'description', 'image_url', 'github_url', 'max_supply', 'consensus_type', 'network_layer']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✓ Updated {CSV_FILE}")
    print(f"✓ Images stored in {OUTPUT_DIR}")


if __name__ == '__main__':
    try:
        download_all_images()
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)
