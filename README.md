AI-Powered Outdoor Activity Weather Advisor 🌤️
This is a desktop application built with Python and Tkinter that provides AI-powered weather suitability analysis for various outdoor activities. It helps users plan events by not only showing the weather forecast but also scoring each day's suitability based on user-defined or preset preferences for temperature, wind, and rain.

The application fetches historical weather data from NASA POWER to train a set of scikit-learn models, enabling it to provide more nuanced predictions beyond a simple forecast.

Features ✨
🤖 AI-Powered Analysis: Uses RandomForestClassifier models trained on historical data to predict conditions like 'hot', 'cold', 'windy', or 'wet'.

🎯 Customizable Activities: Choose from a list of predefined activities (like Beach Day, Hiking, Camping) or define your own custom activity with specific weather preferences.

📍 Interactive Location Picker: Search for any city worldwide or click directly on the interactive map to select your event location (requires tkintermapview).

📊 Detailed Daily Breakdown: Get a 5-day forecast with a suitability score (0-100), temperature range, wind speed, precipitation, and general conditions for each day.

💡 Actionable Recommendations: Provides an overall assessment and activity-specific tips to help you prepare for your event.

🖥️ User-Friendly GUI: A clean and intuitive interface built with Tkinter.

Screenshot
(A sample screenshot of the application in action)

Installation
Prerequisites
Python 3.8 or newer.

pip (Python package installer).

Setup Instructions
Clone the repository:

Bash

git clone https://github.com/your-username/weather-advisor.git
cd weather-advisor
Create and activate a virtual environment (recommended):

On macOS/Linux:

Bash

python3 -m venv venv
source venv/bin/activate
On Windows:

Bash

python -m venv venv
.\venv\Scripts\activate
Install the required packages:
The project dependencies are listed in requirements.txt. Install them using pip:

Bash

pip install -r requirements.txt
⚠️ Important: Configure Your API Key
This application requires an API key from OpenWeatherMap to fetch forecast and geocoding data. The key is free for a basic level of access.

Get your free API key by signing up at https://openweathermap.org/api.

Open the main.py file.

Locate the API_KEY variable near the top of the MainApplication class.

Replace the placeholder string with your actual API key.

Python

# main.py

class MainApplication:
    def __init__(self):
        """Initialize the main application"""
        # IMPORTANT: Replace "YOUR_API_KEY_HERE" with your actual OpenWeatherMap API key
        self.API_KEY = "YOUR_API_KEY_HERE" # <--- PASTE YOUR KEY HERE

        if self.API_KEY == "YOUR_API_KEY_HERE":
            # ... (error handling)
The application will not work without a valid API key.

🚀 Running the Application
Once you have installed the dependencies and configured your API key, you can run the application from your terminal:

Bash

python main.py
On the first run for a new location, the application will attempt to download several years of historical data from NASA to train the prediction models. This may take a minute, but the trained models will be saved locally in the models/ directory for instant use on subsequent runs.

Project Structure
.
├── models/             # Directory to store trained model and scaler files
├── main.py             # Main application entry point, handles UI and backend integration
├── weather_predictor.py # Core logic for data fetching, model training, and prediction
├── weather_ui.py       # Defines the Tkinter GUI components and layout
└── requirements.txt    # List of Python dependencies
How It Works
Input: The user selects an activity (preset or custom), a location, and a date range.

Model Training (First Run): If no pre-trained models exist for the location, the WeatherPredictor fetches 5 years of historical daily data from the NASA POWER API. It then trains several RandomForestClassifier models to identify 'hot', 'cold', 'windy', 'wet', and 'uncomfortable' days. The trained models (.pkl files) are saved locally.

Forecast Fetching: The application calls the OpenWeatherMap 5-Day Forecast API to get detailed weather data for the selected location.

Suitability Analysis: For each day in the forecast, a suitability score is calculated based on how well the predicted temperature, wind, and rain match the preferences of the chosen activity.

Output: The results, including daily scores, a summary, and actionable tips, are displayed in the GUI.

Dependencies
pandas: For data manipulation.

numpy: For numerical operations.

scikit-learn: For machine learning models.

joblib: For saving and loading ML models.

requests: For making API calls.

tkcalendar: For the date entry widget in the GUI.

tkintermapview: (Optional) For the interactive map widget.