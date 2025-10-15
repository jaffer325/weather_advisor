import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os


class WeatherPredictor:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
        # Activity suitability profiles
        self.activity_profiles = {
            '🏖️ Beach Day': {
                'ideal_temp': (25, 35),
                'max_wind': 30,
                'max_rain': 2,
                'name': 'Beach Day'
            },
            '⛰️ Hiking/Trekking': {
                'ideal_temp': (15, 28),
                'max_wind': 40,
                'max_rain': 5,
                'name': 'Hiking'
            },
            '🎣 Fishing': {
                'ideal_temp': (10, 30),
                'max_wind': 35,
                'max_rain': 8,
                'name': 'Fishing'
            },
            '⛺ Camping': {
                'ideal_temp': (10, 28),
                'max_wind': 45,
                'max_rain': 3,
                'name': 'Camping'
            },
            '🎵 Outdoor Concert': {
                'ideal_temp': (18, 30),
                'max_wind': 25,
                'max_rain': 1,
                'name': 'Outdoor Concert'
            },
            '⚽ Sports/Exercise': {
                'ideal_temp': (15, 28),
                'max_wind': 35,
                'max_rain': 2,
                'name': 'Sports'
            },
            '🚴 Cycling': {
                'ideal_temp': (10, 30),
                'max_wind': 30,
                'max_rain': 3,
                'name': 'Cycling'
            },
            '🏃 Running': {
                'ideal_temp': (10, 25),
                'max_wind': 40,
                'max_rain': 5,
                'name': 'Running'
            },
            '🌅 Sightseeing': {
                'ideal_temp': (15, 32),
                'max_wind': 40,
                'max_rain': 5,
                'name': 'Sightseeing'
            },
            '📸 Photography': {
                'ideal_temp': (10, 35),
                'max_wind': 35,
                'max_rain': 10,
                'name': 'Photography'
            },
            '🎪 Outdoor Event': {
                'ideal_temp': (18, 30),
                'max_wind': 30,
                'max_rain': 2,
                'name': 'Outdoor Event'
            },
            '✈️ Vacation': {
                'ideal_temp': (20, 32),
                'max_wind': 35,
                'max_rain': 5,
                'name': 'Vacation'
            }
        }
        
        self.models = {}
        self.scalers = {}
        self.model_trained = False
        self.load_or_train_models()
    
    def load_or_train_models(self):
        model_dir = 'models'
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        model_types = ['hot', 'cold', 'windy', 'wet', 'uncomfortable']
        
        for model_type in model_types:
            model_path = f'{model_dir}/{model_type}_model.pkl'
            scaler_path = f'{model_dir}/{model_type}_scaler.pkl'
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                try:
                    self.models[model_type] = joblib.load(model_path)
                    self.scalers[model_type] = joblib.load(scaler_path)
                except:
                    self.models[model_type] = None
                    self.scalers[model_type] = None
            else:
                self.models[model_type] = None
                self.scalers[model_type] = None
        
        self.model_trained = any(model is not None for model in self.models.values())
    
    def fetch_nasa_historical_data(self, lat, lon, years=5):
        try:
            end_year = datetime.now().year - 1
            start_year = end_year - years + 1
            
            url = "https://power.larc.nasa.gov/api/temporal/daily/point"
            params = {
                'parameters': 'T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,WS10M,WS10M_MAX,RH2M',
                'community': 'RE',
                'longitude': lon,
                'latitude': lat,
                'start': f"{start_year}0101",
                'end': f"{end_year}1231",
                'format': 'JSON'
            }
            
            response = requests.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'properties' in data and 'parameter' in data['properties']:
                    params_data = data['properties']['parameter']
                    
                    df_data = {}
                    for param, values in params_data.items():
                        df_data[param] = list(values.values())
                    
                    df = pd.DataFrame(df_data)
                    df['date'] = pd.to_datetime(list(params_data['T2M'].keys()), format='%Y%m%d')
                    
                    df = df.replace(-999, np.nan)
                    df = df.dropna()
                    
                    return df
            
            return None
        except Exception as e:
            print(f"Note: Could not fetch historical data: {e}")
            return None
    
    def prepare_training_data(self, historical_data):
        try:
            df = historical_data.copy()
            
            df['month'] = df['date'].dt.month
            df['day_of_year'] = df['date'].dt.dayofyear
            df['season'] = df['month'].apply(lambda x: (x % 12 + 3) // 3)
            
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            df['day_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
            df['day_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365)
            
            df['temp_range'] = df['T2M_MAX'] - df['T2M_MIN']
            df['heat_index'] = df.apply(
                lambda row: self.calculate_heat_index(row['T2M'], row['RH2M']), axis=1
            )
            df['wind_chill'] = df.apply(
                lambda row: self.calculate_wind_chill(row['T2M'], row['WS10M'] * 3.6), axis=1
            )
            
            y_dict = {
                'hot': (df['T2M_MAX'] > 35).astype(int),
                'cold': (df['T2M_MIN'] < 0).astype(int),
                'windy': (df['WS10M_MAX'] * 3.6 > 40).astype(int),
                'wet': (df['PRECTOTCORR'] > 10).astype(int),
                'uncomfortable': ((df['heat_index'] > 32) | (df['wind_chill'] < 0)).astype(int)
            }
            
            feature_cols = [
                'T2M', 'T2M_MAX', 'T2M_MIN', 'WS10M', 'WS10M_MAX', 'RH2M',
                'month', 'season', 'month_sin', 'month_cos', 'day_sin', 'day_cos',
                'temp_range', 'heat_index', 'wind_chill'
            ]
            
            X = df[feature_cols].values
            
            return X, y_dict
            
        except Exception as e:
            print(f"Error preparing training data: {e}")
            return None, None
    
    def train_models_with_historical_data(self, lat, lon):
        print(f"\n🤖 Training AI models with historical data for ({lat:.2f}, {lon:.2f})...")
        
        historical_data = self.fetch_nasa_historical_data(lat, lon, years=5)
        
        if historical_data is None or len(historical_data) < 100:
            print("⚠️ Using rule-based predictions.\n")
            return False
        
        print(f"📊 Processing {len(historical_data)} days of historical data...")
        
        X, y_dict = self.prepare_training_data(historical_data)
        
        if X is None or len(X) < 100:
            print("⚠️ Using rule-based predictions.\n")
            return False
        
        model_dir = 'models'
        
        for condition in ['hot', 'cold', 'windy', 'wet', 'uncomfortable']:
            if condition in y_dict:
                try:
                    y = y_dict[condition]
                    
                    positive_ratio = y.sum() / len(y)
                    
                    if positive_ratio < 0.01 or positive_ratio > 0.99:
                        continue
                    
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.2, random_state=42, stratify=y
                    )
                    
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)
                    
                    model = RandomForestClassifier(
                        n_estimators=100,
                        max_depth=10,
                        min_samples_split=20,
                        min_samples_leaf=10,
                        random_state=42,
                        n_jobs=-1
                    )
                    
                    model.fit(X_train_scaled, y_train)
                    
                    test_score = model.score(X_test_scaled, y_test)
                    
                    print(f"    ✓ {condition} model - Accuracy: {test_score*100:.1f}%")
                    
                    joblib.dump(model, f'{model_dir}/{condition}_model.pkl')
                    joblib.dump(scaler, f'{model_dir}/{condition}_scaler.pkl')
                    
                    self.models[condition] = model
                    self.scalers[condition] = scaler
                    
                except Exception as e:
                    print(f"    Note: Skipping {condition} model")
        
        self.model_trained = any(model is not None for model in self.models.values())
        
        if self.model_trained:
            print("✅ AI models ready!\n")
        
        return self.model_trained
    
    def get_coordinates(self, city, country_code):
        try:
            geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},{country_code}&limit=1&appid={self.api_key}"
            response = requests.get(geocode_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]['lat'], data[0]['lon']
        except:
            pass
        return None, None
    
    def fetch_forecast(self, lat, lon):
        try:
            url = f"{self.base_url}/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching forecast: {e}")
        
        return None
    
    def calculate_heat_index(self, temp_c, humidity):
        if temp_c < 27:
            return temp_c
        
        temp_f = (temp_c * 9/5) + 32
        
        hi = -42.379 + 2.04901523*temp_f + 10.14333127*humidity
        hi -= 0.22475541*temp_f*humidity - 0.00683783*temp_f*temp_f
        hi -= 0.05481717*humidity*humidity + 0.00122874*temp_f*temp_f*humidity
        hi += 0.00085282*temp_f*humidity*humidity - 0.00000199*temp_f*temp_f*humidity*humidity
        
        return (hi - 32) * 5/9
    
    def calculate_wind_chill(self, temp_c, wind_speed_kmh):
        if temp_c > 10 or wind_speed_kmh < 4.8:
            return temp_c
        
        wind_speed_mph = wind_speed_kmh * 0.621371
        temp_f = (temp_c * 9/5) + 32
        
        wc = 35.74 + 0.6215*temp_f - 35.75*(wind_speed_mph**0.16)
        wc += 0.4275*temp_f*(wind_speed_mph**0.16)
        
        return (wc - 32) * 5/9
    
    def calculate_suitability_score(self, weather_data, activity_profile):
        """Calculate how suitable weather is for the activity (0-100)"""
        temp = weather_data['temp']
        wind_speed = weather_data['wind_speed']
        precipitation = weather_data['precipitation']
        
        score = 100
        
        # Temperature scoring
        ideal_min, ideal_max = activity_profile['ideal_temp']
        if ideal_min <= temp <= ideal_max:
            temp_score = 100
        else:
            if temp < ideal_min:
                temp_score = max(0, 100 - (ideal_min - temp) * 5)
            else:
                temp_score = max(0, 100 - (temp - ideal_max) * 5)
        
        # Wind scoring
        if wind_speed <= activity_profile['max_wind']:
            wind_score = 100
        else:
            wind_score = max(0, 100 - (wind_speed - activity_profile['max_wind']) * 3)
        
        # Rain scoring
        if precipitation <= activity_profile['max_rain']:
            rain_score = 100
        else:
            rain_score = max(0, 100 - (precipitation - activity_profile['max_rain']) * 10)
        
        # Combined score with weights
        score = (temp_score * 0.5 + wind_score * 0.25 + rain_score * 0.25)
        
        return score
    
    def get_suitability_rating(self, score):
        """Convert score to rating"""
        if score >= 80:
            return "EXCELLENT", "✅", "#2E7D32"
        elif score >= 60:
            return "GOOD", "👍", "#558B2F"
        elif score >= 40:
            return "FAIR", "⚠️", "#F57C00"
        else:
            return "POOR", "❌", "#D32F2F"
    
    def get_activity_tips(self, activity_name):
        """Get activity-specific tips"""
        tips = []
        
        activity_lower = activity_name.lower()
        
        if 'beach' in activity_lower:
            tips = [
                "• Check UV index for sun protection",
                "• Monitor tide schedules",
                "• Stay hydrated in the sun",
                "• Bring reef-safe sunscreen"
            ]
        elif 'hik' in activity_lower or 'camp' in activity_lower or 'trek' in activity_lower:
            tips = [
                "• Pack layers for temperature changes",
                "• Bring rain gear even if low probability",
                "• Check trail conditions before departure",
                "• Inform someone of your route"
            ]
        elif 'cycl' in activity_lower or 'run' in activity_lower or 'jog' in activity_lower:
            tips = [
                "• Avoid peak heat hours (11am-3pm)",
                "• Wear reflective gear if low visibility",
                "• Stay hydrated throughout",
                "• Check air quality index"
            ]
        elif 'concert' in activity_lower or 'event' in activity_lower or 'festival' in activity_lower:
            tips = [
                "• Arrive early to secure good spots",
                "• Bring rain ponchos just in case",
                "• Wear comfortable shoes",
                "• Stay hydrated"
            ]
        elif 'fish' in activity_lower:
            tips = [
                "• Check local fishing regulations",
                "• Best times are dawn and dusk",
                "• Monitor wind conditions closely",
                "• Bring sun protection"
            ]
        elif 'photo' in activity_lower:
            tips = [
                "• Golden hour: 1 hour after sunrise/before sunset",
                "• Overcast days great for portraits",
                "• Protect equipment from moisture",
                "• Check sunrise/sunset times"
            ]
        elif 'sport' in activity_lower or 'exercise' in activity_lower:
            tips = [
                "• Warm up properly",
                "• Stay hydrated",
                "• Watch for heat exhaustion signs",
                "• Have indoor backup plan"
            ]
        else:
            tips = [
                "• Check weather updates regularly",
                "• Have a backup plan ready",
                "• Dress appropriately for conditions",
                "• Stay safe and enjoy!"
            ]
        
        return tips
    
    def predict(self, input_data):
        try:
            lat = float(input_data['latitude'])
            lon = float(input_data['longitude'])
            
            # Train models if not already trained
            if not self.model_trained:
                self.train_models_with_historical_data(lat, lon)
            
            # Fetch forecast data
            forecast_data = self.fetch_forecast(lat, lon)
            if not forecast_data:
                return "❌ Error: Could not fetch weather forecast data."
            
            # Get activity profile
            activity = input_data['event_type']
            
            # Check if custom parameters provided
            if 'custom_params' in input_data:
                profile = input_data['custom_params']
            else:
                profile = self.activity_profiles.get(activity, {
                    'ideal_temp': (15, 30),
                    'max_wind': 35,
                    'max_rain': 5,
                    'name': 'Outdoor Activity'
                })
            
            # Build results
            results = []
            results.append(f"\n{'='*70}")
            results.append(f"🌤️  WEATHER SUITABILITY ANALYSIS")
            results.append(f"{'='*70}")
            results.append(f"\n📍 Location: {input_data['city']}, {input_data['country']}")
            results.append(f"🎯 Activity: {profile['name']}")
            results.append(f"📅 Date: {input_data['date']} ({input_data['duration']} days)")
            results.append(f"🌡️  Preferences: {profile['ideal_temp'][0]}°C - {profile['ideal_temp'][1]}°C | ")
            results.append(f"    Wind ≤{profile['max_wind']} km/h | Rain ≤{profile['max_rain']} mm")
            results.append(f"{'='*70}\n")
            
            # Process forecast by day
            daily_data = {}
            for item in forecast_data['list'][:input_data['duration']*8]:
                dt = datetime.fromtimestamp(item['dt'])
                day_key = dt.strftime('%Y-%m-%d')
                
                if day_key not in daily_data:
                    daily_data[day_key] = {
                        'temps': [],
                        'temp_maxs': [],
                        'temp_mins': [],
                        'winds': [],
                        'wind_gusts': [],
                        'humidity': [],
                        'precipitation': 0,
                        'weather_desc': item['weather'][0]['description'],
                        'weather_main': item['weather'][0]['main']
                    }
                
                daily_data[day_key]['temps'].append(item['main']['temp'])
                daily_data[day_key]['temp_maxs'].append(item['main']['temp_max'])
                daily_data[day_key]['temp_mins'].append(item['main']['temp_min'])
                daily_data[day_key]['winds'].append(item['wind']['speed'] * 3.6)
                daily_data[day_key]['wind_gusts'].append(item['wind'].get('gust', item['wind']['speed']) * 3.6)
                daily_data[day_key]['humidity'].append(item['main']['humidity'])
                daily_data[day_key]['precipitation'] += item.get('rain', {}).get('3h', 0) + item.get('snow', {}).get('3h', 0)
            
            # Analyze each day
            day_scores = []
            results.append("📊 DAILY FORECAST & SUITABILITY:\n")
            results.append("-" * 70)
            
            for day_key in sorted(daily_data.keys()):
                day_info = daily_data[day_key]
                
                weather = {
                    'temp': np.mean(day_info['temps']),
                    'temp_max': max(day_info['temp_maxs']),
                    'temp_min': min(day_info['temp_mins']),
                    'wind_speed': np.mean(day_info['winds']),
                    'wind_max': max(day_info['wind_gusts']),
                    'humidity': np.mean(day_info['humidity']),
                    'precipitation': day_info['precipitation']
                }
                
                score = self.calculate_suitability_score(weather, profile)
                rating, emoji, color = self.get_suitability_rating(score)
                day_scores.append(score)
                
                results.append(f"\n📅 {day_key}")
                results.append(f"   {emoji} Suitability: {rating} ({score:.0f}/100)")
                results.append(f"   🌡️  Temperature: {weather['temp']:.1f}°C (High: {weather['temp_max']:.1f}°C, Low: {weather['temp_min']:.1f}°C)")
                results.append(f"   💨 Wind: {weather['wind_speed']:.1f} km/h (Gusts: {weather['wind_max']:.1f} km/h)")
                results.append(f"   💧 Humidity: {weather['humidity']:.0f}%")
                results.append(f"   🌧️  Precipitation: {weather['precipitation']:.1f} mm")
                results.append(f"   ☁️  Conditions: {day_info['weather_desc'].capitalize()}")
                
                # Specific recommendations
                issues = []
                if weather['temp_max'] > profile['ideal_temp'][1]:
                    issues.append(f"⚠️ May be too hot (>{profile['ideal_temp'][1]}°C)")
                elif weather['temp_min'] < profile['ideal_temp'][0]:
                    issues.append(f"⚠️ May be too cold (<{profile['ideal_temp'][0]}°C)")
                
                if weather['wind_max'] > profile['max_wind']:
                    issues.append(f"⚠️ High winds expected (>{profile['max_wind']} km/h)")
                
                if weather['precipitation'] > profile['max_rain']:
                    issues.append(f"⚠️ Heavy rain expected (>{profile['max_rain']} mm)")
                
                if issues:
                    results.append(f"   ⚠️  Concerns: {', '.join(issues)}")
            
            results.append(f"\n{'-' * 70}")
            
            # Overall summary
            avg_score = np.mean(day_scores)
            overall_rating, overall_emoji, _ = self.get_suitability_rating(avg_score)
            
            results.append(f"\n{'='*70}")
            results.append(f"📊 OVERALL ASSESSMENT:")
            results.append(f"{'='*70}")
            results.append(f"\n{overall_emoji} Overall Suitability: {overall_rating} ({avg_score:.0f}/100)")
            
            # Recommendations
            results.append(f"\n💡 RECOMMENDATIONS:\n")
            
            if avg_score >= 80:
                results.append("✅ Excellent conditions for your activity!")
                results.append("   • Weather is ideal - go ahead with your plans")
                results.append("   • Still bring sunscreen and stay hydrated")
            elif avg_score >= 60:
                results.append("👍 Good conditions overall")
                results.append("   • Weather is suitable for your activity")
                results.append("   • Check forecast updates closer to the date")
            elif avg_score >= 40:
                results.append("⚠️  Fair conditions - proceed with caution")
                results.append("   • Have backup plans ready")
                results.append("   • Bring appropriate gear for conditions")
                results.append("   • Monitor weather forecasts closely")
            else:
                results.append("❌ Poor conditions for this activity")
                results.append("   • Consider rescheduling if possible")
                results.append("   • If proceeding, take extra precautions")
                results.append("   • Have indoor alternatives ready")
            
            # Activity-specific tips
            results.append(f"\n📋 TIPS FOR {profile['name'].upper()}:")
            tips = self.get_activity_tips(profile['name'])
            for tip in tips:
                results.append(f"   {tip}")
            
            results.append(f"\n{'='*70}")
            results.append("⚡ Powered by AI Weather Analysis")
            results.append(f"{'='*70}\n")
            
            return '\n'.join(results)
            
        except Exception as e:
            import traceback
            return f"❌ Error during prediction:\n{str(e)}\n\n{traceback.format_exc()}"