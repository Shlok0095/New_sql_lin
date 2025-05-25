import os
import sys
import subprocess
import site

print("Reinstalling Streamlit and dependencies...")

try:
    # Uninstall Streamlit and its dependencies
    dependencies = ['streamlit', 'blinker', 'click', 'protobuf', 'watchdog']
    
    for dep in dependencies:
        print(f"Uninstalling {dep}...")
        try:
            subprocess.call([sys.executable, '-m', 'pip', 'uninstall', '-y', dep])
        except Exception as e:
            print(f"Error uninstalling {dep}: {e}")
    
    # Install Streamlit
    print("\nInstalling Streamlit...")
    subprocess.call([sys.executable, '-m', 'pip', 'install', 'streamlit'])
    
    # Verify installation
    print("\nVerifying installation...")
    try:
        print("Testing blinker import...")
        from blinker import Signal
        print("SUCCESS: blinker.Signal can be imported")
        
        print("Testing streamlit import...")
        import streamlit
        print(f"SUCCESS: Streamlit {streamlit.__version__} installed correctly")
        
        print("\nStreamlit reinstalled successfully!")
        print("You can now run: streamlit run streamlit_app.py")
    except ImportError as e:
        print(f"ERROR: Import failed: {e}")
        print("Reinstallation was not completely successful.")
        
except Exception as e:
    print(f"Error during reinstallation: {e}")
    print("\nPLEASE TRY MANUALLY:")
    print("1. Deactivate your virtual environment")
    print("2. Create a new virtual environment")
    print("3. Install required packages: pip install -r requirements.txt") 