import pandas as pd
import networkx as nx
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import time
import base64

# Page config
st.set_page_config(
    page_title="Campus GPS Navigation",
    page_icon="🗺️",
    layout="wide"
)

# Custom CSS for GPS page only
st.markdown("""
<style>
    .gps-container {
        max-width: 500px;
        margin: 50px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .gps-icon {
        font-size: 64px;
        margin-bottom: 20px;
    }
    
    .gps-title {
        font-size: 28px;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 10px;
    }
    
    .gps-subtitle {
        color: #666;
        margin-bottom: 30px;
    }
    
    .stButton > button {
        width: 100%;
        margin: 5px 0;
    }
    
    .manual-section {
        margin-top: 20px;
        padding: 20px;
        background: #f8f9fa;
        border-radius: 10px;
    }
    
    .voice-direction {
        background: #f0f7ff;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #2196F3;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(-20px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .time-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 30px;
        display: inline-block;
        font-weight: bold;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# Load Data
# ----------------------------
@st.cache_data
def load_data():
    nodes = pd.read_excel("Nodes_sheet - 1.xlsx", sheet_name="Nodes")
    edges = pd.read_excel("Edges_with_distance.xlsx")
    
    nodes = nodes.dropna(subset=["Id", "Name", "Latitude", "Longitude"])
    edges = edges.dropna(subset=["From", "To", "Distance_m"])
    
    nodes["Id"] = nodes["Id"].astype(int)
    edges["From"] = edges["From"].astype(int)
    edges["To"] = edges["To"].astype(int)
    
    return nodes, edges

nodes, edges = load_data()

# Build graph
G = nx.Graph()

for _, row in nodes.iterrows():
    G.add_node(
        row["Id"],
        name=row["Name"],
        pos=(row["Latitude"], row["Longitude"])
    )

for _, row in edges.iterrows():
    G.add_edge(
        row["From"],
        row["To"],
        weight=row["Distance_m"]
    )

# Create mappings
name_to_id = {row["Name"].strip(): row["Id"] for _, row in nodes.iterrows()}
id_to_name = {row["Id"]: row["Name"].strip() for _, row in nodes.iterrows()}

# Initialize session state
if "current_lat" not in st.session_state:
    st.session_state["current_lat"] = nodes["Latitude"].mean()
    st.session_state["current_lon"] = nodes["Longitude"].mean()
    st.session_state["gps_accuracy"] = None
    st.session_state["gps_locked"] = False
    st.session_state["destination"] = None
    st.session_state["path"] = None
    st.session_state["tracking"] = False
    st.session_state["show_gps"] = True
    st.session_state["show_manual"] = False
    st.session_state["voice_enabled"] = True

# ----------------------------
# Helper Functions
# ----------------------------
def get_direction_instruction(from_node, to_node, distance):
    """Generate a natural language direction"""
    from_name = id_to_name[from_node]
    to_name = id_to_name[to_node]
    
    # Get coordinates to determine general direction
    from_row = nodes[nodes["Id"] == from_node].iloc[0]
    to_row = nodes[nodes["Id"] == to_node].iloc[0]
    
    # Simple direction logic based on coordinate differences
    lat_diff = to_row["Latitude"] - from_row["Latitude"]
    lon_diff = to_row["Longitude"] - from_row["Longitude"]
    
    if abs(lat_diff) > abs(lon_diff):
        direction = "north" if lat_diff > 0 else "south"
    else:
        direction = "east" if lon_diff > 0 else "west"
    
    return f"Walk {direction} for {distance:.0f} meters to {to_name}"

def text_to_speech(text):
    """Convert text to speech using browser's speech synthesis"""
    audio_html = f"""
    <script>
        var msg = new SpeechSynthesisUtterance();
        msg.text = "{text}";
        msg.rate = 0.9;
        msg.pitch = 1;
        window.speechSynthesis.cancel(); // Stop any ongoing speech
        window.speechSynthesis.speak(msg);
    </script>
    """
    return audio_html

def format_walking_time(distance_meters):
    """Convert distance to walking time"""
    avg_walking_speed = 1.4  # meters per second
    time_seconds = distance_meters / avg_walking_speed
    
    if time_seconds < 60:
        return f"{time_seconds:.0f} seconds"
    elif time_seconds < 3600:
        minutes = time_seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = time_seconds / 3600
        return f"{hours:.1f} hours"

# ----------------------------
# GPS Page with Auto-redirect
# ----------------------------
if st.session_state["show_gps"] and not st.session_state["gps_locked"]:
    
    # Center the GPS container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="gps-container">
            <div class="gps-icon">📍</div>
            <div class="gps-title">Location Required</div>
            <div class="gps-subtitle">We need your location for accurate campus navigation</div>
        </div>
        """, unsafe_allow_html=True)
        
        # GPS button using JavaScript with URL redirect
        gps_html = """
        <div style="text-align: center;">
            <button onclick="getLocation()" style="
                background: #4CAF50;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                margin: 10px 0;
                transition: all 0.3s;
            ">
                🎯 Get My Location
            </button>
            
            <button onclick="showManual()" style="
                background: #2196F3;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                margin: 10px 0;
                transition: all 0.3s;
            ">
                ✏️ Enter Coordinates Manually
            </button>
            
            <div id="manual-section" style="display: none; margin-top: 20px;">
                <input type="text" id="lat-input" placeholder="Latitude (e.g., 6.69152)" style="
                    width: 100%;
                    padding: 12px;
                    margin: 5px 0;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    font-size: 14px;
                ">
                <input type="text" id="lon-input" placeholder="Longitude (e.g., -1.60957)" style="
                    width: 100%;
                    padding: 12px;
                    margin: 5px 0;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    font-size: 14px;
                ">
                <button onclick="submitManual()" style="
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 12px;
                    border-radius: 8px;
                    font-size: 16px;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 10px;
                ">
                    Submit Coordinates
                </button>
            </div>
            
            <div id="status" style="
                margin-top: 20px;
                padding: 15px;
                border-radius: 8px;
                display: none;
                font-weight: 500;
            "></div>
        </div>
        
        <script>
        function showStatus(message, isError) {
            const status = document.getElementById('status');
            status.style.display = 'block';
            status.style.background = isError ? '#ffebee' : '#e8f5e8';
            status.style.color = isError ? '#c62828' : '#2e7d32';
            status.innerHTML = message;
        }
        
        function getLocation() {
            showStatus('🛰️ Requesting GPS...', false);
            
            if (!navigator.geolocation) {
                showStatus('❌ GPS is not supported by your browser', true);
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    const acc = position.coords.accuracy;
                    
                    showStatus(`✅ GPS locked! Accuracy: ${acc.toFixed(1)}m`, false);
                    
                    // Auto-redirect to map page with coordinates
                    setTimeout(() => {
                        window.location.href = window.location.pathname + 
                            '?lat=' + lat + 
                            '&lon=' + lon + 
                            '&acc=' + acc +
                            '&gps=success';
                    }, 1500);
                },
                (error) => {
                    let msg = '❌ ';
                    if (error.code === 1) {
                        msg += 'Please allow location access in your browser';
                    } else if (error.code === 2) {
                        msg += 'GPS unavailable. Try going outside';
                    } else if (error.code === 3) {
                        msg += 'GPS timeout. Please try again';
                    } else {
                        msg += 'GPS error: ' + error.message;
                    }
                    showStatus(msg, true);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        }
        
        function showManual() {
            document.getElementById('manual-section').style.display = 'block';
        }
        
        function submitManual() {
            const lat = document.getElementById('lat-input').value;
            const lon = document.getElementById('lon-input').value;
            
            if (!lat || !lon) {
                showStatus('❌ Please enter both coordinates', true);
                return;
            }
            
            const latNum = parseFloat(lat);
            const lonNum = parseFloat(lon);
            
            if (isNaN(latNum) || isNaN(lonNum)) {
                showStatus('❌ Please enter valid numbers', true);
                return;
            }
            
            showStatus('✅ Manual location set! Redirecting...', false);
            
            // Auto-redirect with manual coordinates
            setTimeout(() => {
                window.location.href = window.location.pathname + 
                    '?lat=' + latNum + 
                    '&lon=' + lonNum + 
                    '&acc=5' +
                    '&manual=success';
            }, 1500);
        }
        </script>
        """
        
        st.components.v1.html(gps_html, height=500)
        
        # Check URL parameters for GPS data
        query_params = st.query_params if hasattr(st, 'query_params') else {}
        
        # Check for GPS success
        if 'gps' in query_params and query_params['gps'] == 'success':
            try:
                st.session_state["current_lat"] = float(query_params['lat'])
                st.session_state["current_lon"] = float(query_params['lon'])
                st.session_state["gps_accuracy"] = float(query_params.get('acc', [10])[0])
                st.session_state["gps_locked"] = True
                st.session_state["show_gps"] = False
                # Clear URL parameters
                if hasattr(st, 'query_params'):
                    st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error processing GPS data: {e}")
        
        # Check for manual success
        if 'manual' in query_params and query_params['manual'] == 'success':
            try:
                st.session_state["current_lat"] = float(query_params['lat'])
                st.session_state["current_lon"] = float(query_params['lon'])
                st.session_state["gps_accuracy"] = float(query_params.get('acc', [5])[0])
                st.session_state["gps_locked"] = True
                st.session_state["show_gps"] = False
                if hasattr(st, 'query_params'):
                    st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error processing manual coordinates: {e}")

else:
    # ----------------------------
    # Main Navigation UI with Voice & Walking Time
    # ----------------------------
    st.title("📍 Campus Navigation System")
    
    # Settings row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state["gps_accuracy"]:
            acc = st.session_state["gps_accuracy"]
            if acc < 10:
                st.success(f"🟢 GPS: {acc:.0f}m")
            elif acc < 30:
                st.warning(f"🟡 GPS: {acc:.0f}m")
            else:
                st.error(f"🔴 GPS: {acc:.0f}m")
    
    with col2:
        source = "GPS" if st.session_state.get("gps_accuracy", 0) < 50 else "Manual"
        st.info(f"📍 {source}")
    
    with col3:
        # Voice toggle
        voice_enabled = st.toggle("🔊 Voice Guidance", value=st.session_state.get("voice_enabled", True))
        st.session_state["voice_enabled"] = voice_enabled
    
    with col4:
        if st.button("🔄 New Location", use_container_width=True):
            st.session_state["show_gps"] = True
            st.session_state["gps_locked"] = False
            st.rerun()
    
    # Check if on campus
    campus_bounds = {
        "min_lat": nodes["Latitude"].min() - 0.001,
        "max_lat": nodes["Latitude"].max() + 0.001,
        "min_lon": nodes["Longitude"].min() - 0.001,
        "max_lon": nodes["Longitude"].max() + 0.001
    }
    
    on_campus = (
        campus_bounds["min_lat"] <= st.session_state["current_lat"] <= campus_bounds["max_lat"] and
        campus_bounds["min_lon"] <= st.session_state["current_lon"] <= campus_bounds["max_lon"]
    )
    
    if on_campus:
        st.success("✅ You are on campus")
    else:
        st.warning("⚠️ You are off campus - navigation may not be accurate")
    
    # Main navigation columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🎯 Destination")
        buildings = sorted(nodes["Name"].str.strip().tolist())
        dest = st.selectbox("Select destination", buildings)
        
        if st.button("🚀 Find Route", type="primary", use_container_width=True):
            st.session_state["destination"] = name_to_id[dest]
            
            # Find nearest node
            min_dist = float('inf')
            nearest = None
            for _, row in nodes.iterrows():
                dist = geodesic(
                    (st.session_state["current_lat"], st.session_state["current_lon"]),
                    (row["Latitude"], row["Longitude"])
                ).meters
                if dist < min_dist:
                    min_dist = dist
                    nearest = row["Id"]
            
            st.session_state["current_node"] = nearest
            
            try:
                path = nx.shortest_path(G, nearest, st.session_state["destination"], weight="weight")
                distance = nx.shortest_path_length(G, nearest, st.session_state["destination"], weight="weight")
                
                st.session_state["path"] = path
                st.session_state["total_distance"] = distance
                st.session_state["tracking"] = True
                st.success(f"✅ Route found!")
                st.rerun()
            except nx.NetworkXNoPath:
                st.error("❌ No path found to destination!")
        
        if st.session_state.get("tracking") and st.session_state.get("path"):
            if st.button("🛑 Clear Route", use_container_width=True):
                st.session_state["tracking"] = False
                st.session_state["path"] = None
                st.rerun()
        
        # Show distance and walking time
        if st.session_state.get("total_distance"):
            distance = st.session_state["total_distance"]
            walking_time = format_walking_time(distance)
            
            st.markdown(f"""
            <div class="time-badge">
                📏 Distance: {distance:.0f}m
            </div>
            <div class="time-badge" style="background: linear-gradient(135deg, #ff6b6b 0%, #ff8e8e 100%);">
                ⏱️ Walking: {walking_time}
            </div>
            """, unsafe_allow_html=True)
        
        # Voice directions
        if st.session_state.get("tracking") and st.session_state.get("path") and st.session_state["voice_enabled"]:
            st.markdown("### 🗣️ Voice Directions")
            
            path = st.session_state["path"]
            
            # Generate all directions
            directions_text = []
            for i in range(len(path) - 1):
                from_node = path[i]
                to_node = path[i + 1]
                segment_dist = G[from_node][to_node]["weight"]
                
                direction = get_direction_instruction(from_node, to_node, segment_dist)
                directions_text.append(direction)
                
                st.markdown(f"""
                <div class="voice-direction">
                    <b>Step {i+1}:</b> {direction}
                </div>
                """, unsafe_allow_html=True)
            
            # Play all directions as audio (one after another with delay)
            if st.button("🔊 Play All Directions"):
                full_text = ". ".join(directions_text)
                st.components.v1.html(text_to_speech(full_text), height=0)
    
    with col2:
        st.markdown("### 🗺️ Map")
        
        # Create map
        m = folium.Map(
            location=[st.session_state["current_lat"], st.session_state["current_lon"]],
            zoom_start=18
        )
        
        # Add buildings
        for _, row in nodes.iterrows():
            if st.session_state.get("destination") == row["Id"]:
                color = "red"
                icon = "flag"
            elif st.session_state.get("path") and row["Id"] in st.session_state["path"]:
                color = "blue"
                icon = "circle"
            else:
                color = "gray"
                icon = "info-sign"
            
            folium.Marker(
                [row["Latitude"], row["Longitude"]],
                popup=row["Name"],
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(m)
        
        # Draw route with segment distances
        if st.session_state.get("path"):
            route_coords = []
            for i in range(len(st.session_state["path"]) - 1):
                from_node = st.session_state["path"][i]
                to_node = st.session_state["path"][i + 1]
                
                from_row = nodes[nodes["Id"] == from_node].iloc[0]
                to_row = nodes[nodes["Id"] == to_node].iloc[0]
                
                route_coords.append([from_row["Latitude"], from_row["Longitude"]])
                route_coords.append([to_row["Latitude"], to_row["Longitude"]])
                
                # Add distance label mid-way
                mid_lat = (from_row["Latitude"] + to_row["Latitude"]) / 2
                mid_lon = (from_row["Longitude"] + to_row["Longitude"]) / 2
                
                segment_dist = G[from_node][to_node]["weight"]
                
                folium.Marker(
                    [mid_lat, mid_lon],
                    popup=f"{segment_dist:.0f}m",
                    icon=folium.DivIcon(html=f'<div style="font-size: 12pt; font-weight: bold;">{segment_dist:.0f}m</div>')
                ).add_to(m)
            
            # Draw the route line
            folium.PolyLine(
                route_coords,
                color="blue",
                weight=4,
                opacity=0.8
            ).add_to(m)
        
        # Current location
        folium.Marker(
            [st.session_state["current_lat"], st.session_state["current_lon"]],
            popup="You are here",
            icon=folium.Icon(color="green", icon="location-dot", prefix="fa")
        ).add_to(m)
        
        # Accuracy circle
        if st.session_state.get("gps_accuracy"):
            folium.Circle(
                [st.session_state["current_lat"], st.session_state["current_lon"]],
                radius=st.session_state["gps_accuracy"],
                color="green" if st.session_state["gps_accuracy"] < 10 else "orange",
                fill=True,
                fillOpacity=0.1
            ).add_to(m)
        
        st_folium(m, width=None, height=500)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <b>📍 Campus Navigation System</b><br>
    <small>With Voice Guidance • Real-time GPS • Walking Time Estimates</small>
</div>
""", unsafe_allow_html=True)