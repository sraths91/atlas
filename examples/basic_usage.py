"""
Basic usage example for Atlas
"""
from atlas.app import Atlas

def main():
    """Run the basic example"""
    print("Starting Atlas in simulated mode...")
    print("Press Ctrl+C to stop")
    
    # Create app instance with simulated display
    app = Atlas(simulated=True)
    
    # Run the application
    app.run()

if __name__ == "__main__":
    main()
