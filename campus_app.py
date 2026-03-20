import pandas as pd
import networkx as nx
import streamlit as st
import folium
from streamlit_folium import st_folium

# ----------------------------
# Load Data
# ----------------------------
nodes = pd.read_excel("Nodes_sheet - 1.xlsx", sheet_name="Nodes")
edges = pd.read_excel("Edges_with_distance.xlsx")

# Clean data
nodes = nodes.dropna(subset=["Id", "Name", "Latitude", "Longitude"])
edges = edges.dropna(subset=["From", "To", "Distance_m"])

nodes["Id"] = nodes["Id"].astype(int)
edges["From"] = edges["From"].astype(int)
edges["To"] = edges["To"].astype(int)

# ----------------------------
# Build Graph
# ----------------------------
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

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("Campus Navigation System 🗺️")

buildings = nodes["Name"].str.strip().tolist()

start_name = st.selectbox("Select Start Location", buildings)
end_name = st.selectbox("Select Destination", buildings)

# Session state
if "coords" not in st.session_state:
    st.session_state["coords"] = None
if "distance" not in st.session_state:
    st.session_state["distance"] = None
if "route_names" not in st.session_state:
    st.session_state["route_names"] = None

# ----------------------------
# Find Route Button
# ----------------------------
if st.button("Find Route"):
    # Create lookup dictionary
    name_to_id = {
        row["Name"].strip(): row["Id"]
        for _, row in nodes.iterrows()
    }
    
    start = name_to_id[start_name]
    end = name_to_id[end_name]
    
    try:
        # Calculate shortest path
        path = nx.shortest_path(G, start, end, weight="weight")
        distance = nx.shortest_path_length(G, start, end, weight="weight")
        
        # Get coordinates for the path
        coords = []
        route_names = []
        
        for node in path:
            row = nodes[nodes["Id"] == node].iloc[0]
            coords.append((row["Latitude"], row["Longitude"]))
            route_names.append(row["Name"].strip())
        
        # Store in session state
        st.session_state["coords"] = coords
        st.session_state["distance"] = distance
        st.session_state["route_names"] = route_names
        
    except nx.NetworkXNoPath:
        st.error("❌ No walking path exists between these locations.")
        st.session_state["coords"] = None
        st.session_state["distance"] = None
        st.session_state["route_names"] = None

# ----------------------------
# Display Results
# ----------------------------
if st.session_state["coords"]:
    # Show distance
    st.success(f"📏 Total Distance: {st.session_state['distance']:.2f} meters")
    
    # Show step-by-step directions
    st.write("### 🧭 Directions")
    route_names = st.session_state["route_names"]
    for i in range(len(route_names) - 1):
        st.write(f"➡️ From **{route_names[i]}** → **{route_names[i+1]}**")
    
    # Create map
    first = nodes.iloc[0]
    m = folium.Map(
        location=[first["Latitude"], first["Longitude"]],
        zoom_start=18
    )
    
    # Add markers
    for _, row in nodes.iterrows():
        folium.Marker(
            [row["Latitude"], row["Longitude"]],
            popup=row["Name"],
            icon=folium.Icon(color="green" if row["Name"] in [start_name, end_name] else "blue")
        ).add_to(m)
    
    # Draw route
    folium.PolyLine(
        st.session_state["coords"],
        color="red",
        weight=5,
        opacity=0.8
    ).add_to(m)
    
    st.write("### 🗺️ Route Map")
    st_folium(m, width=900, height=600)