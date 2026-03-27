import pandas as pd
import networkx as nx
import streamlit as st
import folium
from folium.plugins import Fullscreen, LocateControl, MiniMap
from streamlit_folium import st_folium
from geopy.distance import geodesic
import math

# Page config
st.set_page_config(
    page_title="Campus Navigation",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 20px;
    }

    .gps-container {
        max-width: 450px;
        margin: 80px auto;
        padding: 40px;
        background: white;
        border-radius: 25px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.15);
        text-align: center;
    }

    .next-turn-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        margin: 15px 0;
    }

    .next-turn-card h1 {
        font-size: 48px;
        margin: 10px 0;
    }

    .direction-item {
        padding: 12px 15px;
        margin: 8px 0;
        background: #f8f9fa;
        border-radius: 12px;
        border-left: 4px solid #4CAF50;
    }

    .direction-item.completed {
        opacity: 0.5;
        border-left-color: #6c757d;
        text-decoration: line-through;
    }

    .direction-item.current {
        background: #e3f2fd;
        border-left-color: #2196F3;
        font-weight: 600;
    }

    .progress-bar {
        background: #e0e0e0;
        border-radius: 10px;
        height: 8px;
        margin: 15px 0;
        overflow: hidden;
    }

    .progress-fill {
        background: linear-gradient(90deg, #4CAF50, #2196F3);
        height: 100%;
        transition: width 0.5s ease;
    }

    .entrance-badge {
        background: #ff9800;
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
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
    G.add_node(row["Id"], name=row["Name"], pos=(row["Latitude"], row["Longitude"]))

for _, row in edges.iterrows():
    G.add_edge(row["From"], row["To"], weight=row["Distance_m"])

# Create mappings
name_to_id = {row["Name"].strip(): row["Id"] for _, row in nodes.iterrows()}
id_to_name = {row["Id"]: row["Name"].strip() for _, row in nodes.iterrows()}

# Entrance IDs
ENTRANCE_IDS = [2, 16, 30, 33]
ENTRANCE_NAMES = {2: "Entrance 3", 16: "Entrance 4", 30: "Main Entrance 1", 33: "Entrance 2"}

# Campus bounds
CAMPUS_MIN_LAT = nodes["Latitude"].min()
CAMPUS_MAX_LAT = nodes["Latitude"].max()
CAMPUS_MIN_LON = nodes["Longitude"].min()
CAMPUS_MAX_LON = nodes["Longitude"].max()

# ----------------------------
# Helper Functions
# ----------------------------
def get_bearing(lat1, lon1, lat2, lon2):
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360

def get_direction(bearing):
    directions = ["North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"]
    idx = round(bearing / 45) % 8
    return directions[idx]

def find_nearest_node(lat, lon):
    min_dist = float('inf')
    nearest = None
    for _, row in nodes.iterrows():
        dist = geodesic((lat, lon), (row["Latitude"], row["Longitude"])).meters
        if dist < min_dist:
            min_dist = dist
            nearest = row["Id"]
    return nearest, min_dist

def find_nearest_entrance(lat, lon):
    min_dist = float('inf')
    nearest = None
    nearest_name = None
    for ent_id in ENTRANCE_IDS:
        row = nodes[nodes["Id"] == ent_id].iloc[0]
        dist = geodesic((lat, lon), (row["Latitude"], row["Longitude"])).meters
        if dist < min_dist:
            min_dist = dist
            nearest = ent_id
            nearest_name = row["Name"]
    return nearest, min_dist, nearest_name

def is_on_campus(lat, lon):
    for _, row in nodes.iterrows():
        dist = geodesic((lat, lon), (row["Latitude"], row["Longitude"])).meters
        if dist < 50:
            return True
    return False

def get_direct_instruction(from_lat, from_lon, to_lat, to_lon, to_name):
    bearing = get_bearing(from_lat, from_lon, to_lat, to_lon)
    direction = get_direction(bearing)
    dist = geodesic((from_lat, from_lon), (to_lat, to_lon)).meters
    return f"Walk {direction} for {dist:.0f} meters to {to_name}", direction, dist

def get_route_instruction(from_node, to_node):
    from_row = nodes[nodes["Id"] == from_node].iloc[0]
    to_row = nodes[nodes["Id"] == to_node].iloc[0]
    bearing = get_bearing(from_row["Latitude"], from_row["Longitude"],
                          to_row["Latitude"], to_row["Longitude"])
    direction = get_direction(bearing)
    dist = G[from_node][to_node]["weight"]
    return f"Head {direction} for {dist:.0f} meters to {id_to_name[to_node]}", direction, dist

def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    else:
        return f"{seconds/3600:.1f}h"

def speak(text):
    speech_html = f"""
    <script>
    var utterance = new SpeechSynthesisUtterance("{text}");
    utterance.rate = 0.9;
    utterance.pitch = 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    </script>
    """
    st.components.v1.html(speech_html, height=0)

def build_map(current_lat, current_lon, gps_accuracy, full_coords, total_distance,
              nearest_entrance, destination_id, full_path):
    """Build the Folium map centered and fitted to show the full campus."""

    all_lats = nodes["Latitude"].tolist()
    all_lons = nodes["Longitude"].tolist()
    campus_center_lat = sum(all_lats) / len(all_lats)
    campus_center_lon = sum(all_lons) / len(all_lons)

    m = folium.Map(
        location=[campus_center_lat, campus_center_lon],
        zoom_start=17,
        control_scale=True,
        tiles="OpenStreetMap"
    )

    # Fit map bounds to show entire campus (with small padding)
    sw = [min(all_lats) - 0.0008, min(all_lons) - 0.0008]
    ne = [max(all_lats) + 0.0008, max(all_lons) + 0.0008]
    m.fit_bounds([sw, ne])

    # ── Fullscreen button (top-right, like Google Maps) ──────────────────
    Fullscreen(
        position="topright",
        title="Full Screen",
        title_cancel="Exit Full Screen",
        force_separate_button=True
    ).add_to(m)

    # ── Live "locate me" button ───────────────────────────────────────────
    LocateControl(
        position="topright",
        strings={"title": "My Location"},
        locate_options={"enableHighAccuracy": True},
        auto_start=False
    ).add_to(m)

    # ── Mini overview map (bottom-right corner) ───────────────────────────
    MiniMap(
        position="bottomright",
        tile_layer="OpenStreetMap",
        zoom_level_offset=-5,
        toggle_display=True
    ).add_to(m)

    # Collect destination and route node IDs for color coding
    route_node_ids = set()
    if full_path:
        for seg in full_path:
            if seg.get("type") == "campus":
                route_node_ids.add(seg.get("from_node"))
                route_node_ids.add(seg.get("to_node"))

    # Add all buildings as CircleMarkers (compact, no overlap)
    for _, row in nodes.iterrows():
        nid = row["Id"]
        name = row["Name"].strip()

        if nid == destination_id:
            color = "#e74c3c"
            border_color = "#c0392b"
            radius = 10
            label = f"🏁 {name} (Destination)"
        elif nid in ENTRANCE_IDS:
            color = "#f39c12"
            border_color = "#d68910"
            radius = 8
            label = f"🚪 {name} (Entrance)"
        elif nid in route_node_ids:
            color = "#2980b9"
            border_color = "#1a5276"
            radius = 7
            label = f"➡️ {name}"
        else:
            color = "#34495e"
            border_color = "#1c2833"
            radius = 5
            label = name

        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=radius,
            color=border_color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(label, max_width=200),
            tooltip=name
        ).add_to(m)

    # Draw full route line
    if full_coords and len(full_coords) >= 2:
        folium.PolyLine(
            full_coords,
            color="#2980b9",
            weight=5,
            opacity=0.85,
            tooltip=f"Route: {total_distance:.0f}m"
        ).add_to(m)

    # Nearest entrance special highlight
    if nearest_entrance:
        ent_row = nodes[nodes["Id"] == nearest_entrance].iloc[0]
        folium.CircleMarker(
            location=[ent_row["Latitude"], ent_row["Longitude"]],
            radius=12,
            color="#e67e22",
            weight=3,
            fill=True,
            fill_color="#f39c12",
            fill_opacity=0.9,
            popup=folium.Popup(f"🚪 {ent_row['Name']} (Your Entry Point)", max_width=200),
            tooltip=f"Entry: {ent_row['Name']}"
        ).add_to(m)

    # Current user location
    folium.Marker(
        location=[current_lat, current_lon],
        popup="📍 You are here",
        tooltip="Your Location",
        icon=folium.Icon(color="green", icon="location-dot", prefix="fa")
    ).add_to(m)

    # GPS accuracy circle
    if gps_accuracy:
        folium.Circle(
            location=[current_lat, current_lon],
            radius=gps_accuracy,
            color="green" if gps_accuracy < 10 else "orange",
            fill=True,
            fill_opacity=0.1
        ).add_to(m)

    return m


# ----------------------------
# Initialize Session State
# ----------------------------
if "current_lat" not in st.session_state:
    st.session_state.current_lat = None
    st.session_state.current_lon = None
    st.session_state.gps_accuracy = None
    st.session_state.gps_locked = False
    st.session_state.show_gps = True
    st.session_state.destination = None
    st.session_state.full_path = None
    st.session_state.full_instructions = []
    st.session_state.full_coords = []
    st.session_state.tracking = False
    st.session_state.current_step = 0
    st.session_state.completed_steps = []
    st.session_state.last_spoken = None
    st.session_state.voice_enabled = True
    st.session_state.total_distance = 0
    st.session_state.nearest_entrance = None
    st.session_state.dist_to_entrance = 0


# ----------------------------
# GPS Location Page
# ----------------------------
if st.session_state.show_gps and not st.session_state.gps_locked:

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div class="gps-container">
            <div style="font-size: 60px;">📍</div>
            <h2>Campus Navigation</h2>
            <p>Allow location access to start navigating from anywhere</p>
        </div>
        """, unsafe_allow_html=True)

        gps_html = """
        <div style="text-align: center;">
            <button onclick="getLocation()" style="
                background: #4CAF50;
                color: white;
                border: none;
                padding: 16px 32px;
                border-radius: 50px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                width: 100%;
                box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
            ">
                📍 Get My Location
            </button>
            <div id="gps-status" style="margin-top: 20px; padding: 12px; border-radius: 10px; display: none;"></div>
        </div>

        <script>
        function showStatus(msg, isError) {
            const div = document.getElementById('gps-status');
            div.style.display = 'block';
            div.style.background = isError ? '#ffebee' : '#e8f5e8';
            div.style.color = isError ? '#c62828' : '#2e7d32';
            div.innerHTML = msg;
        }

        function getLocation() {
            showStatus('🛰️ Getting your location...', false);

            if (!navigator.geolocation) {
                showStatus('❌ GPS not supported', true);
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    showStatus('✅ Location acquired!', false);
                    setTimeout(() => {
                        window.location.href = window.location.pathname +
                            '?lat=' + pos.coords.latitude +
                            '&lon=' + pos.coords.longitude +
                            '&acc=' + pos.coords.accuracy;
                    }, 800);
                },
                (err) => {
                    let msg = '❌ ';
                    if (err.code === 1) msg += 'Please allow location access';
                    else if (err.code === 2) msg += 'GPS unavailable';
                    else msg += 'GPS error';
                    showStatus(msg, true);
                },
                { enableHighAccuracy: true, timeout: 15000 }
            );
        }
        </script>
        """

        st.components.v1.html(gps_html, height=300)

        query_params = st.query_params
        if 'lat' in query_params and 'lon' in query_params:
            st.session_state.current_lat = float(query_params['lat'])
            st.session_state.current_lon = float(query_params['lon'])
            st.session_state.gps_accuracy = float(query_params.get('acc', [10])[0])
            st.session_state.gps_locked = True
            st.session_state.show_gps = False
            st.query_params.clear()
            st.rerun()


# ----------------------------
# Main Navigation Screen
# ----------------------------
else:

    st.markdown(
        '<div class="main-header"><h1>📍 Campus Navigation</h1>'
        '<p>From anywhere to your destination • Live GPS • Voice Guidance</p></div>',
        unsafe_allow_html=True
    )

    on_campus = is_on_campus(st.session_state.current_lat, st.session_state.current_lon)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.session_state.gps_accuracy:
            acc = st.session_state.gps_accuracy
            if acc < 10:
                st.success(f"🟢 GPS: {acc:.0f}m")
            elif acc < 30:
                st.warning(f"🟡 GPS: {acc:.0f}m")
            else:
                st.error(f"🔴 GPS: {acc:.0f}m")

    with col2:
        if on_campus:
            st.success("✅ ON CAMPUS")
        else:
            st.warning("📍 OFF CAMPUS — Will guide you to campus first")

    with col3:
        st.session_state.voice_enabled = st.toggle("🔊 Voice", value=st.session_state.voice_enabled)

    with col4:
        if st.button("📍 New Location", use_container_width=True):
            st.session_state.show_gps = True
            st.session_state.gps_locked = False
            st.session_state.tracking = False
            st.rerun()

    st.markdown("---")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("### 🎯 Destination")
        buildings = sorted(nodes["Name"].str.strip().tolist())
        selected_dest = st.selectbox("Where do you want to go?", buildings, label_visibility="collapsed")

        if st.button("🚀 Start Navigation", type="primary", use_container_width=True):
            dest_id = name_to_id[selected_dest]
            st.session_state.destination = dest_id

            st.session_state.full_path = []
            st.session_state.full_instructions = []
            st.session_state.full_coords = []

            entrance_id, dist_to_entrance, entrance_name = find_nearest_entrance(
                st.session_state.current_lat,
                st.session_state.current_lon
            )
            st.session_state.nearest_entrance = entrance_id
            st.session_state.dist_to_entrance = dist_to_entrance

            try:
                campus_path = nx.shortest_path(G, entrance_id, dest_id, weight="weight")
                campus_distance = nx.shortest_path_length(G, entrance_id, dest_id, weight="weight")

                entrance_coords = nodes[nodes["Id"] == entrance_id].iloc[0]

                # Direct segment: user → entrance
                st.session_state.full_path.append({
                    "type": "direct",
                    "from_lat": st.session_state.current_lat,
                    "from_lon": st.session_state.current_lon,
                    "to_lat": entrance_coords["Latitude"],
                    "to_lon": entrance_coords["Longitude"],
                    "to_name": entrance_name,
                    "distance": dist_to_entrance
                })

                # Campus segments
                for i in range(len(campus_path) - 1):
                    st.session_state.full_path.append({
                        "type": "campus",
                        "from_node": campus_path[i],
                        "to_node": campus_path[i + 1],
                        "distance": G[campus_path[i]][campus_path[i + 1]]["weight"]
                    })

                # Instructions
                inst, dir_text, d = get_direct_instruction(
                    st.session_state.current_lat, st.session_state.current_lon,
                    entrance_coords["Latitude"], entrance_coords["Longitude"],
                    entrance_name
                )
                st.session_state.full_instructions.append({
                    "text": inst,
                    "direction": dir_text,
                    "distance": d,
                    "target": entrance_name,
                    "type": "direct"
                })

                for i in range(len(campus_path) - 1):
                    inst, dir_text, d = get_route_instruction(campus_path[i], campus_path[i + 1])
                    st.session_state.full_instructions.append({
                        "text": inst,
                        "direction": dir_text,
                        "distance": d,
                        "target": id_to_name[campus_path[i + 1]],
                        "type": "campus"
                    })

                # Full coordinate line for map
                st.session_state.full_coords.append([st.session_state.current_lat, st.session_state.current_lon])
                st.session_state.full_coords.append([entrance_coords["Latitude"], entrance_coords["Longitude"]])
                for node_id in campus_path:
                    r = nodes[nodes["Id"] == node_id].iloc[0]
                    st.session_state.full_coords.append([r["Latitude"], r["Longitude"]])

                st.session_state.total_distance = dist_to_entrance + campus_distance
                st.session_state.tracking = True
                st.session_state.current_step = 0
                st.session_state.completed_steps = []

                if not on_campus:
                    st.success(
                        f"📍 {dist_to_entrance:.0f}m to {entrance_name}, "
                        f"then {campus_distance:.0f}m inside campus"
                    )
                else:
                    st.success(f"✅ Route found! {campus_distance:.0f}m to destination")

            except Exception as e:
                st.error(f"Cannot find route: {e}")

            st.rerun()

        if st.session_state.tracking and st.session_state.full_instructions:
            st.markdown("---")
            st.metric("Total Distance", f"{st.session_state.total_distance:.0f} m")
            st.metric("Est. Walking Time", format_time(st.session_state.total_distance / 1.4))

            if st.button("🛑 Stop Navigation", use_container_width=True):
                st.session_state.tracking = False
                st.rerun()

    with col_right:
        # Build and render the map (campus-centered, fully visible)
        m = build_map(
            current_lat=st.session_state.current_lat,
            current_lon=st.session_state.current_lon,
            gps_accuracy=st.session_state.gps_accuracy,
            full_coords=st.session_state.full_coords,
            total_distance=st.session_state.total_distance,
            nearest_entrance=st.session_state.nearest_entrance,
            destination_id=st.session_state.destination,
            full_path=st.session_state.full_path or []
        )
        st_folium(m, width="100%", height=600, returned_objects=[])


    # ----------------------------
    # Live Turn-by-Turn Navigation
    # ----------------------------
    if st.session_state.tracking and st.session_state.full_instructions:

        st.markdown("---")
        st.markdown("### 🧭 Live Navigation")

        current_node, _ = find_nearest_node(st.session_state.current_lat, st.session_state.current_lon)

        if current_node == st.session_state.destination:
            st.balloons()
            st.success("🎉 You have reached your destination!")
            st.session_state.tracking = False
            st.rerun()

        current_idx = st.session_state.current_step

        if current_idx < len(st.session_state.full_instructions):
            inst = st.session_state.full_instructions[current_idx]

            if inst["type"] == "direct":
                ent_row = nodes[nodes["Id"] == st.session_state.nearest_entrance].iloc[0]
                dist_to_ent = geodesic(
                    (st.session_state.current_lat, st.session_state.current_lon),
                    (ent_row["Latitude"], ent_row["Longitude"])
                ).meters
                if dist_to_ent < 20:
                    st.session_state.current_step += 1
                    st.rerun()
            else:
                for seg in st.session_state.full_path:
                    if seg.get("type") == "campus" and seg.get("to_node") == current_node:
                        st.session_state.current_step += 1
                        st.rerun()
                        break

        if st.session_state.current_step < len(st.session_state.full_instructions):
            inst = st.session_state.full_instructions[st.session_state.current_step]

            st.markdown(f"""
            <div class="next-turn-card">
                <p style="font-size: 14px; opacity: 0.9;">⬆️ NEXT</p>
                <h1>{inst['direction']}</h1>
                <p style="font-size: 20px; font-weight: bold;">{inst['distance']:.0f} m</p>
                <p style="font-size: 14px;">to {inst['target']}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.voice_enabled and st.session_state.last_spoken != inst['text']:
                st.session_state.last_spoken = inst['text']
                speak(inst['text'])

            total_steps = len(st.session_state.full_instructions)
            progress = (st.session_state.current_step + 1) / total_steps

            remaining_dist = sum(
                st.session_state.full_instructions[i]['distance']
                for i in range(st.session_state.current_step, len(st.session_state.full_instructions))
            )

            st.markdown(f"""
            <div class="progress-bar">
                <div class="progress-fill" style="width: {progress * 100}%;"></div>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>📍 Step {st.session_state.current_step + 1} of {total_steps}</span>
                <span>⏱️ {format_time(remaining_dist / 1.4)} remaining</span>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("📋 All Directions"):
            for i, inst in enumerate(st.session_state.full_instructions):
                if i < st.session_state.current_step:
                    st.markdown(
                        f'<div class="direction-item completed">✅ {i+1}. {inst["text"]}</div>',
                        unsafe_allow_html=True
                    )
                elif i == st.session_state.current_step:
                    st.markdown(
                        f'<div class="direction-item current">📍 {i+1}. {inst["text"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="direction-item">➡️ {i+1}. {inst["text"]}</div>',
                        unsafe_allow_html=True
                    )

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666; font-size: 12px;'>"
    "📍 From anywhere to anywhere • Live GPS • Turn-by-Turn • Voice Guidance</p>",
    unsafe_allow_html=True
)