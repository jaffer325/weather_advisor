import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkcalendar import DateEntry
from datetime import datetime
import requests
import threading

try:
    from tkintermapview import TkinterMapView
    MAP_AVAILABLE = True
except:
    MAP_AVAILABLE = False
    print("⚠️ tkintermapview not installed. Map feature disabled.")
    print("Install with: pip install tkintermapview")


class AutocompleteEntry(tk.Entry):
    """Entry widget with autocomplete dropdown"""
    def __init__(self, master, autocomplete_function, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.autocomplete_function = autocomplete_function
        self.var = tk.StringVar()
        self.config(textvariable=self.var)
        self.listbox = None
        self.listbox_visible = False
        self.city_suggestions = []
        
        self.var.trace('w', self.on_change)
        self.bind('<KeyRelease>', self.on_keyrelease)
        self.bind('<Down>', self.on_down)
        self.bind('<Up>', self.on_up)
        self.bind('<Return>', self.on_select)
        self.bind('<FocusOut>', self.on_focus_out)
    
    def on_change(self, *args):
        text = self.var.get()
        if len(text) >= 2:
            threading.Thread(target=self.fetch_suggestions, args=(text,), daemon=True).start()
        else:
            self.hide_listbox()
    
    def fetch_suggestions(self, text):
        suggestions, self.city_suggestions = self.autocomplete_function(text)
        if suggestions:
            self.after(0, lambda: self.show_listbox(suggestions))
        else:
            self.after(0, self.hide_listbox)
    
    def show_listbox(self, suggestions):
        if self.listbox:
            self.listbox.destroy()
        
        self.listbox = tk.Listbox(self.master, height=min(8, len(suggestions)), font=("Arial", 10))
        self.listbox.place(
            x=self.winfo_x(),
            y=self.winfo_y() + self.winfo_height(),
            width=self.winfo_width() + 200
        )
        
        for item in suggestions:
            self.listbox.insert(tk.END, item)
        
        self.listbox.bind('<Button-1>', self.on_listbox_click)
        self.listbox.bind('<Return>', self.on_listbox_click)
        self.listbox_visible = True
    
    def hide_listbox(self):
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None
            self.listbox_visible = False
    
    def on_focus_out(self, event):
        self.after(200, self.hide_listbox)
    
    def on_keyrelease(self, event):
        if event.keysym in ('Down', 'Up', 'Return', 'Escape'):
            return
    
    def on_down(self, event):
        if self.listbox_visible and self.listbox:
            current = self.listbox.curselection()
            if current:
                index = current[0]
                if index < self.listbox.size() - 1:
                    self.listbox.selection_clear(index)
                    self.listbox.selection_set(index + 1)
            else:
                self.listbox.selection_set(0)
            return 'break'
    
    def on_up(self, event):
        if self.listbox_visible and self.listbox:
            current = self.listbox.curselection()
            if current:
                index = current[0]
                if index > 0:
                    self.listbox.selection_clear(index)
                    self.listbox.selection_set(index - 1)
            return 'break'
    
    def on_select(self, event):
        if self.listbox_visible and self.listbox:
            selection = self.listbox.curselection()
            if selection:
                self.var.set(self.listbox.get(selection[0]))
                self.hide_listbox()
            return 'break'
    
    def on_listbox_click(self, event):
        if self.listbox:
            selection = self.listbox.curselection()
            if selection:
                self.var.set(self.listbox.get(selection[0]))
            self.hide_listbox()


class WeatherPredictionUI:
    def __init__(self, root, prediction_callback, api_key):
        self.root = root
        self.prediction_callback = prediction_callback
        self.api_key = api_key
        self.root.title("🌤️ Outdoor Activity Weather Advisor - AI Powered")
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Set window size
        window_width = int(screen_width * 0.9)
        window_height = int(screen_height * 0.85)
        
        # Center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.configure(bg="#f5f5f5")
        
        self.selected_location = None
        self.map_marker = None
        self.city_suggestions_data = []
        
        # Predefined activities
        self.predefined_activities = {
            '🏖️ Beach Day': {'ideal_temp': (25, 35), 'max_wind': 30, 'max_rain': 2},
            '⛰️ Hiking/Trekking': {'ideal_temp': (15, 28), 'max_wind': 40, 'max_rain': 5},
            '🎣 Fishing': {'ideal_temp': (10, 30), 'max_wind': 35, 'max_rain': 8},
            '⛺ Camping': {'ideal_temp': (10, 28), 'max_wind': 45, 'max_rain': 3},
            '🎵 Outdoor Concert': {'ideal_temp': (18, 30), 'max_wind': 25, 'max_rain': 1},
            '⚽ Sports/Exercise': {'ideal_temp': (15, 28), 'max_wind': 35, 'max_rain': 2},
            '🚴 Cycling': {'ideal_temp': (10, 30), 'max_wind': 30, 'max_rain': 3},
            '🏃 Running': {'ideal_temp': (10, 25), 'max_wind': 40, 'max_rain': 5},
            '🌅 Sightseeing': {'ideal_temp': (15, 32), 'max_wind': 40, 'max_rain': 5},
            '📸 Photography': {'ideal_temp': (10, 35), 'max_wind': 35, 'max_rain': 10},
            '🎪 Outdoor Event': {'ideal_temp': (18, 30), 'max_wind': 30, 'max_rain': 2},
            '✈️ Vacation': {'ideal_temp': (20, 32), 'max_wind': 35, 'max_rain': 5},
        }
        
        self.create_widgets()
    
    def search_cities(self, query):
        """Search cities using OpenWeatherMap Geocoding API"""
        try:
            url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=10&appid={self.api_key}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                suggestions = []
                suggestions_data = []
                
                for item in data:
                    city_name = item.get('name', '')
                    state = item.get('state', '')
                    country = item.get('country', '')
                    lat = item.get('lat', 0)
                    lon = item.get('lon', 0)
                    
                    display = f"{city_name}"
                    if state:
                        display += f", {state}"
                    display += f", {country}"
                    
                    suggestions.append(display)
                    suggestions_data.append({
                        'display': display,
                        'name': city_name,
                        'state': state,
                        'country': country,
                        'lat': lat,
                        'lon': lon
                    })
                
                return suggestions, suggestions_data
            return [], []
        except Exception as e:
            print(f"Error searching cities: {e}")
            return [], []
    
    def autocomplete_city(self, text):
        """Autocomplete function for city entry"""
        displays, self.city_suggestions_data = self.search_cities(text)
        return displays, self.city_suggestions_data
    
    def on_city_selected(self, *args):
        """Handle city selection - automatically fills coordinates"""
        selected_text = self.city_autocomplete.var.get()
        
        # Look through stored suggestions
        for suggestion in self.city_autocomplete.city_suggestions:
            if suggestion['display'] == selected_text:
                self.selected_location = suggestion
                
                # Update map if available
                if MAP_AVAILABLE and hasattr(self, 'map_widget'):
                    self.update_map_location(suggestion['lat'], suggestion['lon'])
                
                # Show location info
                self.location_info_label.config(
                    text=f"📍 {suggestion['name']}, {suggestion['country']} | 🌍 {suggestion['lat']:.4f}, {suggestion['lon']:.4f}",
                    fg="#1976D2"
                )
                return
    
    def update_map_location(self, lat, lon):
        """Update map marker position"""
        if MAP_AVAILABLE and hasattr(self, 'map_widget'):
            try:
                self.map_widget.set_position(lat, lon)
                self.map_widget.set_zoom(10)
                
                # Remove old marker
                if self.map_marker:
                    self.map_marker.delete()
                
                # Add new marker
                self.map_marker = self.map_widget.set_marker(lat, lon, text="📍 Event Location")
            except Exception as e:
                print(f"Map update error: {e}")
    
    def on_map_click(self, coords):
        """Handle map click to select location"""
        lat, lon = coords
        
        # Update marker
        if self.map_marker:
            self.map_marker.delete()
        
        if MAP_AVAILABLE and hasattr(self, 'map_widget'):
            self.map_marker = self.map_widget.set_marker(lat, lon, text="📍 Event Location")
        
        # Reverse geocode to get city name
        threading.Thread(target=self.reverse_geocode, args=(lat, lon), daemon=True).start()
    
    def reverse_geocode(self, lat, lon):
        """Get city name from coordinates"""
        try:
            url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={self.api_key}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    city = data[0].get('name', '')
                    state = data[0].get('state', '')
                    country = data[0].get('country', '')
                    
                    display = f"{city}"
                    if state:
                        display += f", {state}"
                    display += f", {country}"
                    
                    # Store location
                    self.selected_location = {
                        'name': city,
                        'state': state,
                        'country': country,
                        'lat': lat,
                        'lon': lon,
                        'display': display
                    }
                    
                    # Update UI in main thread
                    self.root.after(0, lambda: self.city_autocomplete.var.set(display))
                    self.root.after(0, lambda: self.location_info_label.config(
                        text=f"📍 {city}, {country} | 🌍 {lat:.4f}, {lon:.4f}",
                        fg="#1976D2"
                    ))
        except Exception as e:
            print(f"Reverse geocode error: {e}")
    
    def on_activity_mode_change(self):
        """Handle switching between preset and custom activity"""
        if self.activity_mode.get() == "preset":
            self.preset_frame.pack(fill="x", pady=(0, 8))
            self.custom_frame.pack_forget()
        else:
            self.preset_frame.pack_forget()
            self.custom_frame.pack(fill="x", pady=(0, 8))
    
    def create_widgets(self):
        # Main container with two columns
        main_container = tk.Frame(self.root, bg="#f5f5f5")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left Panel - Input Controls
        left_panel = tk.Frame(main_container, bg="#f5f5f5", width=480)
        left_panel.pack(side=tk.LEFT, fill="both", padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Right Panel - Results and Map
        right_panel = tk.Frame(main_container, bg="#f5f5f5")
        right_panel.pack(side=tk.LEFT, fill="both", expand=True)
        
        # Title
        title_frame = tk.Frame(left_panel, bg="#1976D2", height=100)
        title_frame.pack(fill="x", pady=(0, 15))
        title_frame.pack_propagate(False)
        
        title = tk.Label(
            title_frame,
            text="🌤️ Weather Advisor",
            font=("Arial", 22, "bold"),
            bg="#1976D2",
            fg="white"
        )
        title.pack(pady=15)
        
        subtitle = tk.Label(
            title_frame,
            text="Plan Your Perfect Outdoor Activity",
            font=("Arial", 11),
            bg="#1976D2",
            fg="#E3F2FD"
        )
        subtitle.pack()
        
        # Scrollable frame for inputs
        canvas = tk.Canvas(left_panel, bg="#f5f5f5", highlightthickness=0)
        scrollbar = tk.Scrollbar(left_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f5f5f5")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Activity Type - ENHANCED
        event_frame = tk.LabelFrame(
            scrollable_frame,
            text="🎯 Activity Configuration",
            font=("Arial", 13, "bold"),
            bg="white",
            fg="#1976D2",
            relief="flat",
            bd=2
        )
        event_frame.pack(fill="x", pady=12, padx=10)
        
        activity_inner = tk.Frame(event_frame, bg="white")
        activity_inner.pack(padx=20, pady=15, fill="x")
        
        # Radio buttons for preset vs custom
        self.activity_mode = tk.StringVar(value="preset")
        
        mode_frame = tk.Frame(activity_inner, bg="white")
        mode_frame.pack(fill="x", pady=(0, 12))
        
        tk.Radiobutton(
            mode_frame, text="Preset Activity", variable=self.activity_mode,
            value="preset", command=self.on_activity_mode_change,
            bg="white", font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Radiobutton(
            mode_frame, text="Custom Activity", variable=self.activity_mode,
            value="custom", command=self.on_activity_mode_change,
            bg="white", font=("Arial", 10)
        ).pack(side=tk.LEFT)
        
        # Preset activity frame
        self.preset_frame = tk.Frame(activity_inner, bg="white")
        self.preset_frame.pack(fill="x", pady=(0, 8))
        
        tk.Label(self.preset_frame, text="Select activity:", bg="white", font=("Arial", 10)).pack(anchor="w", pady=(0, 8))
        
        self.event_type = ttk.Combobox(self.preset_frame, width=35, font=("Arial", 11), state="readonly")
        self.event_type['values'] = tuple(self.predefined_activities.keys())
        self.event_type.current(0)
        self.event_type.pack(fill="x")
        
        # Custom activity frame (hidden by default)
        self.custom_frame = tk.Frame(activity_inner, bg="white")
        
        tk.Label(self.custom_frame, text="Activity name:", bg="white", font=("Arial", 10)).pack(anchor="w", pady=(0, 8))
        self.custom_activity_name = tk.Entry(self.custom_frame, font=("Arial", 11))
        self.custom_activity_name.pack(fill="x", ipady=5, pady=(0, 12))
        
        # Custom parameters
        params_frame = tk.Frame(self.custom_frame, bg="white")
        params_frame.pack(fill="x")
        
        # Temperature range
        temp_frame = tk.Frame(params_frame, bg="white")
        temp_frame.pack(fill="x", pady=(0, 8))
        tk.Label(temp_frame, text="Ideal temp range (°C):", bg="white", font=("Arial", 9)).pack(anchor="w")
        temp_inputs = tk.Frame(temp_frame, bg="white")
        temp_inputs.pack(fill="x")
        self.temp_min = tk.Spinbox(temp_inputs, from_=-20, to=50, width=8, font=("Arial", 10))
        self.temp_min.delete(0, tk.END)
        self.temp_min.insert(0, "15")
        self.temp_min.pack(side=tk.LEFT)
        tk.Label(temp_inputs, text=" to ", bg="white").pack(side=tk.LEFT)
        self.temp_max = tk.Spinbox(temp_inputs, from_=-20, to=50, width=8, font=("Arial", 10))
        self.temp_max.delete(0, tk.END)
        self.temp_max.insert(0, "30")
        self.temp_max.pack(side=tk.LEFT)
        
        # Max wind
        wind_frame = tk.Frame(params_frame, bg="white")
        wind_frame.pack(fill="x", pady=(0, 8))
        tk.Label(wind_frame, text="Max wind speed (km/h):", bg="white", font=("Arial", 9)).pack(anchor="w")
        self.max_wind = tk.Spinbox(wind_frame, from_=0, to=100, width=8, font=("Arial", 10))
        self.max_wind.delete(0, tk.END)
        self.max_wind.insert(0, "35")
        self.max_wind.pack(anchor="w")
        
        # Max rain
        rain_frame = tk.Frame(params_frame, bg="white")
        rain_frame.pack(fill="x")
        tk.Label(rain_frame, text="Max precipitation (mm):", bg="white", font=("Arial", 9)).pack(anchor="w")
        self.max_rain = tk.Spinbox(rain_frame, from_=0, to=50, width=8, font=("Arial", 10))
        self.max_rain.delete(0, tk.END)
        self.max_rain.insert(0, "5")
        self.max_rain.pack(anchor="w")
        
        # Location
        location_frame = tk.LabelFrame(
            scrollable_frame,
            text="📍 Location (Search or Click Map)",
            font=("Arial", 13, "bold"),
            bg="white",
            fg="#1976D2",
            relief="flat",
            bd=2
        )
        location_frame.pack(fill="x", pady=12, padx=10)
        
        location_inner = tk.Frame(location_frame, bg="white")
        location_inner.pack(padx=20, pady=15, fill="x")
        
        tk.Label(location_inner, text="🔍 Search for a city:", bg="white", font=("Arial", 10)).pack(anchor="w", pady=(0, 8))
        
        self.city_autocomplete = AutocompleteEntry(
            location_inner, self.autocomplete_city, font=("Arial", 11)
        )
        self.city_autocomplete.pack(fill="x", ipady=5)
        self.city_autocomplete.var.trace('w', self.on_city_selected)
        self.city_autocomplete.insert(0, "New York")
        
        # Trigger initial selection
        self.root.after(100, lambda: self.on_city_selected())
        
        self.location_info_label = tk.Label(
            location_inner, text="", bg="white", fg="#666", font=("Arial", 9, "italic")
        )
        self.location_info_label.pack(anchor="w", pady=(8, 0))
        
        # Date Selection
        date_frame = tk.LabelFrame(
            scrollable_frame,
            text="📆 Date & Duration",
            font=("Arial", 13, "bold"),
            bg="white",
            fg="#1976D2",
            relief="flat",
            bd=2
        )
        date_frame.pack(fill="x", pady=12, padx=10)
        
        date_inner = tk.Frame(date_frame, bg="white")
        date_inner.pack(padx=20, pady=15, fill="x")
        
        tk.Label(date_inner, text="When?", bg="white", font=("Arial", 10)).pack(anchor="w", pady=(0, 8))
        
        date_row = tk.Frame(date_inner, bg="white")
        date_row.pack(fill="x", pady=(0, 12))
        
        self.date_entry = DateEntry(
            date_row, width=18, background='#1976D2',
            foreground='white', borderwidth=2, font=("Arial", 11)
        )
        self.date_entry.pack(side=tk.LEFT)
        
        tk.Label(date_inner, text="How many days?", bg="white", font=("Arial", 10)).pack(anchor="w", pady=(0, 8))
        
        duration_frame = tk.Frame(date_inner, bg="white")
        duration_frame.pack(fill="x")
        
        self.duration = tk.Spinbox(duration_frame, from_=1, to=14, width=10, font=("Arial", 11))
        self.duration.pack(side=tk.LEFT)
        tk.Label(duration_frame, text="days", bg="white", font=("Arial", 10)).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        
        # Predict Button
        predict_btn = tk.Button(
            scrollable_frame,
            text="🔮 Analyze Weather Suitability",
            command=self.on_predict,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 15, "bold"),
            padx=20,
            pady=18,
            cursor="hand2",
            relief="flat",
            activebackground="#45a049"
        )
        predict_btn.pack(pady=25, padx=10, fill="x")
        
        # RIGHT PANEL - Map and Results
        if MAP_AVAILABLE:
            # Map widget
            map_label = tk.Label(
                right_panel, text="🗺️ Interactive Map - Click to Select Location",
                font=("Arial", 13, "bold"), bg="#f5f5f5", fg="#1976D2"
            )
            map_label.pack(pady=(0, 8))
            
            map_frame = tk.Frame(right_panel, bg="white", relief="solid", bd=2)
            map_frame.pack(fill="both", expand=False, pady=(0, 15))
            map_frame.config(height=350)
            map_frame.pack_propagate(False)
            
            try:
                self.map_widget = TkinterMapView(map_frame, corner_radius=0)
                self.map_widget.pack(fill="both", expand=True)
                self.map_widget.set_position(40.7128, -74.0060)
                self.map_widget.set_zoom(10)
                self.map_widget.add_left_click_map_command(self.on_map_click)
            except Exception as e:
                error_label = tk.Label(
                    map_frame, text=f"Map Error: {e}",
                    bg="white", fg="red"
                )
                error_label.pack(expand=True)
        
        # Results Area
        results_label = tk.Label(
            right_panel, text="📊 Weather Suitability Analysis",
            font=("Arial", 13, "bold"), bg="#f5f5f5", fg="#1976D2"
        )
        results_label.pack(pady=(0, 8))
        
        results_frame = tk.Frame(right_panel, bg="white", relief="solid", bd=2)
        results_frame.pack(fill="both", expand=True)
        
        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#fafafa",
            relief="flat",
            padx=10,
            pady=10
        )
        self.results_text.pack(fill="both", expand=True)
    
    def on_predict(self):
        # Check if location is selected
        if not self.selected_location:
            messagebox.showerror("Error", "Please select a city from the search or click on the map")
            return
        
        # Get activity configuration
        if self.activity_mode.get() == "preset":
            activity_key = self.event_type.get()
            event_type_display = activity_key
        else:
            custom_name = self.custom_activity_name.get().strip()
            if not custom_name:
                messagebox.showerror("Error", "Please enter a custom activity name")
                return
            
            # Create custom activity key with parameters
            event_type_display = f"🎉 {custom_name}"
        
        input_data = {
            'event_type': event_type_display,
            'city': self.selected_location['name'],
            'country': self.selected_location['country'],
            'latitude': str(self.selected_location['lat']),
            'longitude': str(self.selected_location['lon']),
            'date': self.date_entry.get_date(),
            'duration': int(self.duration.get())
        }
        
        # Add custom parameters if in custom mode
        if self.activity_mode.get() == "custom":
            input_data['custom_params'] = {
                'ideal_temp': (int(self.temp_min.get()), int(self.temp_max.get())),
                'max_wind': int(self.max_wind.get()),
                'max_rain': int(self.max_rain.get()),
                'name': custom_name
            }
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "🔄 Analyzing weather conditions and suitability for your activity...\n\n")
        self.results_text.insert(tk.END, "This may take a moment as we fetch data and run AI predictions...\n")
        self.root.update()
        
        try:
            result = self.prediction_callback(input_data)
            self.display_results(result)
        except Exception as e:
            messagebox.showerror("Error", f"Prediction failed: {str(e)}")
    
    def display_results(self, result):
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, result)


if __name__ == "__main__":
    def dummy_prediction(data):
        return f"Testing UI with data:\n{data}"
    
    root = tk.Tk()
    app = WeatherPredictionUI(root, dummy_prediction, "YOUR_API_KEY")
    root.mainloop()