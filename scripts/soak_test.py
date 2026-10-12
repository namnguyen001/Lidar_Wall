import asyncio
import os
import psutil
import time
import requests
import sys

def main():
    print("--- Lidar Wall Kit - Soak Test ---")
    duration_hours = float(os.environ.get("SOAK_HOURS", "0.5"))
    print(f"Running soak test for {duration_hours} hours...")
    
    start_time = time.time()
    end_time = start_time + duration_hours * 3600
    
    p = psutil.Process()
    
    # We assume backend is running on 8080
    base_url = "http://127.0.0.1:8080"
    
    try:
        requests.get(f"{base_url}/api/health", timeout=2)
    except Exception:
        print("Backend is not running. Please start the backend on 8080 first.")
        sys.exit(1)
        
    start_rss = p.memory_info().rss
    max_rss = start_rss
    
    try:
        while time.time() < end_time:
            time.sleep(5)
            
            # Request output test to simulate blobs
            try:
                requests.post(f"{base_url}/api/output/test", timeout=2)
            except Exception as e:
                print(f"Error calling API: {e}")
                
            rss = p.memory_info().rss
            max_rss = max(max_rss, rss)
            
            elapsed = time.time() - start_time
            print(f"Elapsed: {elapsed/60:.1f}m / {duration_hours*60:.1f}m - RSS: {rss/1024/1024:.2f} MB (Max: {max_rss/1024/1024:.2f} MB)", end='\r')
            
    except KeyboardInterrupt:
        print("\nTest interrupted.")
        
    print(f"\n--- Test Completed ---")
    print(f"Initial RSS: {start_rss/1024/1024:.2f} MB")
    print(f"Max RSS: {max_rss/1024/1024:.2f} MB")
    
    diff = max_rss - start_rss
    diff_pct = diff / start_rss * 100 if start_rss > 0 else 0
    print(f"Memory increase: {diff_pct:.2f}%")
    
    if diff_pct > 5.0:
        print("WARNING: RSS increased by more than 5%. Possible memory leak.")
    else:
        print("SUCCESS: Memory stable.")

if __name__ == "__main__":
    main()
