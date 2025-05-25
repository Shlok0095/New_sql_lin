import os
import shutil

# Files to move to backup
files_to_backup = [
    'import_metadata.py',
    'test_metadata_import.py',
    'example_usage.py',
    'USAGE.md',
    'sample_metadata.csv',
    'sample_metadata.json',
    'sample_metadata.sql',
    'exported_metadata.csv',
    'exported_metadata.json',
    'run_app.bat'
]

# Create backup directory if it doesn't exist
backup_dir = os.path.join('backup', 'safe_to_delete')
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

# Move files to backup
print("Moving unnecessary files to backup directory...")
for file in files_to_backup:
    src = file
    dst = os.path.join(backup_dir, file)
    if os.path.exists(src):
        try:
            shutil.move(src, dst)
            print(f"Moved {src} to backup")
        except Exception as e:
            print(f"Error moving {src}: {e}")
    else:
        print(f"{src} not found, skipping")

print("\nCleanup complete. Files moved to backup/safe_to_delete/")
print("Review the backup directory and delete if you're sure you don't need those files.") 