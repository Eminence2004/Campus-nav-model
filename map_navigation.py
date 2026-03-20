import pandas as pd
import networkx as nx
import folium

# Load data
nodes = pd.read_excel("Nodes_sheet - 1.xlsx", sheet_name="Nodes")
edges = pd.read_excel("Edges_with_distance.xlsx")

# Clean data
nodes = nodes.dropna(subset=["Id","Latitude","Longitude"])
edges = edges.dropna(subset=["From","To","Distance_m"])

nodes["Id"] = nodes["Id"].astype(int)
edges["From"] = edges["From"].astype(int)
edges["To"] = edges["To"].astype(int)

# Create graph
G = nx.Graph()

for _, row in nodes.iterrows():
    G.add_node(row["Id"], name=row["Name"],
               pos=(row["Latitude"], row["Longitude"]))

for _, row in edges.iterrows():
    G.add_edge(row["From"], row["To"], weight=row["Distance_m"])

# Ask user
start = int(input("Start node ID: "))
end = int(input("Destination node ID: "))

# Find shortest path
path = nx.shortest_path(G, start, end, weight="weight")

# Create map centered on first node
start_node = nodes.iloc[0]
m = folium.Map(location=[start_node["Latitude"], start_node["Longitude"]], zoom_start=18)

# Add node markers
for _, row in nodes.iterrows():
    folium.Marker(
        [row["Latitude"], row["Longitude"]],
        popup=row["Name"]
    ).add_to(m)

# Draw route
coords = []

for node in path:
    row = nodes[nodes["Id"] == node].iloc[0]
    coords.append((row["Latitude"], row["Longitude"]))

folium.PolyLine(coords, color="blue", weight=5).add_to(m)

# Save map
m.save("campus_route.html")

print("✅ Map saved as campus_route.html")