import tkinter as tk
from tkinter import messagebox
import threading
from weather_ui import WeatherPredictionUI
from weather_predictor import WeatherPredictor

class MainApplication:
    def __init__(self):
        """Initialize the main application"""
        # IMPORTANT: Replace with your actual OpenWeatherMap API key
        # Get free API key at: https://openweathermap.org/api
        self.API_KEY = "Enter your api here"
        
        if self.API_KEY == "YOUR_API_KEY_HERE":
            messagebox.showwarning(
                "API Key Missing",
                "Please set your OpenWeatherMap API key in main.py\n\n"
                "Get a free key at: https://openweathermap.org/api"
            )
        
        # Initialize predictor
        self.predictor = WeatherPredictor(self.API_KEY)
        
        # Create main window
        self.root = tk.Tk()
        
        # Initialize UI with prediction callback and API key
        self.ui = WeatherPredictionUI(self.root, self.handle_prediction, self.API_KEY)
    
    def handle_prediction(self, input_data):
        """
        Handle prediction requests from UI
        Runs prediction in a separate thread to keep UI responsive
        """
        result_container = {'result': None, 'error': None}
        
        def run_prediction():
            try:
                result_container['result'] = self.predictor.predict(input_data)
            except Exception as e:
                result_container['error'] = str(e)
        
        # Run prediction in background thread
        thread = threading.Thread(target=run_prediction)
        thread.daemon = True
        thread.start()
        
        # Wait for thread to complete (with timeout)
        thread.join(timeout=30)
        
        if thread.is_alive():
            return "Error: Prediction is taking too long. Please try again."
        
        if result_container['error']:
            return f"Error: {result_container['error']}"
        
        return result_container['result'] or "No results returned."
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    try:
        app = MainApplication()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        messagebox.showerror("Startup Error", f"Failed to start application:\n{e}")


if __name__ == "__main__":
    main()