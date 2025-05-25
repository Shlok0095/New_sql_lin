"""
Custom blinker module with Signal class to fix the import error in Streamlit.
This is a temporary fix to allow Streamlit to run.
"""

class Signal:
    """
    Basic signal implementation that mimics blinker's Signal class.
    This is a simplified version just to make Streamlit work.
    """
    
    def __init__(self, name, doc=None):
        self.name = name
        self.__doc__ = doc
        self.receivers = {}
    
    def connect(self, receiver, sender=None, weak=True):
        """Connect a receiver to this signal."""
        self.receivers[receiver] = (sender, weak)
        return receiver
    
    def disconnect(self, receiver, sender=None):
        """Disconnect a receiver from this signal."""
        if receiver in self.receivers:
            del self.receivers[receiver]
            return True
        return False
    
    def send(self, sender=None, **kwargs):
        """Emit this signal on behalf of sender, passing on kwargs."""
        results = []
        for receiver, (recv_sender, _) in list(self.receivers.items()):
            if recv_sender is None or recv_sender is sender:
                results.append((receiver, receiver(sender, **kwargs)))
        return results

    def has_receivers_for(self, sender):
        """Return True if there are receivers for sender."""
        return bool(self.receivers_for(sender))
    
    def receivers_for(self, sender):
        """Return a list of receivers connected to sender."""
        return [receiver for receiver, (recv_sender, _) in 
                self.receivers.items()
                if recv_sender is None or recv_sender is sender]

# Add other necessary components from blinker
signal = Signal

def signal_factory(name):
    """Create a new signal with the given name."""
    return Signal(name)

# Add a namespace
NamedSignal = Signal 