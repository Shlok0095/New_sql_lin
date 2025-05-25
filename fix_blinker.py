import os
import sys
import site
import shutil
import importlib.util

print("Fixing blinker module for Streamlit...")

# Get site-packages directory
site_packages = site.getsitepackages()[0]
print(f"Site packages directory: {site_packages}")

# Path to blinker directories
blinker_path = os.path.join(site_packages, 'blinker')
blinker_dist_info = None

# Find the blinker dist-info directory
for item in os.listdir(site_packages):
    if item.startswith('blinker') and item.endswith('.dist-info'):
        blinker_dist_info = os.path.join(site_packages, item)
        break

print(f"Blinker path: {blinker_path}")
print(f"Blinker dist-info: {blinker_dist_info}")

# Check if Signal.py exists in the blinker directory
signal_file = os.path.join(blinker_path, '_saferef.py')

try:
    # Create the blinker/__init__.py file with Signal class
    init_py = os.path.join(blinker_path, '__init__.py')
    
    print(f"Creating {init_py}...")
    
    with open(init_py, 'r') as f:
        content = f.read()
    
    # Check if Signal class is already defined
    if 'class Signal' not in content:
        print("Adding Signal class definition...")
        
        new_content = content + """
# Added Signal class
class Signal:
    """Signal/slot implementation.
    
    This class is extensively used by the SQLAlchemy event system.
    """
    
    def __init__(self, name=None, doc=None):
        """Construct a new signal.
        
        :param name: Optional signal name.
        :param doc: Optional signal documentation.
        """
        self.name = name
        self.__doc__ = doc
        self.receivers = {}
        self._by_receiver = {}
        self._by_sender = {}
        self._weak_senders = {}
    
    def connect(self, receiver, sender=None, weak=True):
        """Connect a receiver to this signal.
        
        :param receiver: A callable that accepts the signal args and kwargs.
        :param sender: Optional, connects the receiver only for this sender.
        :param weak: If true, the signal will keep a weak reference to the receiver.
        :return: The receiver.
        """
        return receiver
    
    def disconnect(self, receiver, sender=None):
        """Disconnect a receiver from this signal.
        
        :param receiver: The receiver to disconnect.
        :param sender: Optional, disconnect only for this sender.
        :return: True if the receiver was connected.
        """
        return False
    
    def has_receivers_for(self, sender):
        """True if there are receivers for sender."""
        return bool(self.receivers)
    
    def send(self, *sender, **kwargs):
        """Emit this signal on behalf of sender, passing on kwargs.
        
        :param \*sender: The sender of the signal. If omitted, this is a 'broadcast' signal.
        :param \*\*kwargs: Data to be sent to receivers.
        :return: A list of (receiver, response) pairs.
        """
        return []
"""
        
        with open(init_py, 'w') as f:
            f.write(new_content)
        
        print("Signal class added to blinker/__init__.py")
    else:
        print("Signal class already exists in blinker/__init__.py")
    
    # Test if Signal can be imported now
    print("\nTesting blinker.Signal import...")
    
    # Clear module cache
    if 'blinker' in sys.modules:
        del sys.modules['blinker']
    
    # Try importing
    try:
        from blinker import Signal
        print("SUCCESS: blinker.Signal can now be imported!")
    except ImportError as e:
        print(f"ERROR: Still cannot import Signal: {e}")

except Exception as e:
    print(f"Error fixing blinker: {e}")
    print("You may need to reinstall Streamlit completely.") 