import pandas as pd
import networkx as nx
import folium

# Function to clean names
def clean(text):
    return str(text).strip().lower().replace("  ", " ")

# Load Excel data
nodes = pd.read_excel("Nodes_sheet - 1.xlsx", sheet_name="Nodes")
edges = pd.read_excel("Edges_with_distance.xlsx")

# Clean data
nodes = nodes.dropna(subset=["Id","Name","Latitude","Longitude"])
edges = edges.dropna(subset=["From","To","Distance_m"])

nodes["Id"] = nodes["Id"].astype(int)
edges["From"] = edges["From"].astype(int)
edges["To"] = edges["To"].astype(int)

# Create graph
G = nx.Graph()

for _, row in nodes.iterrows():
    G.add_node(
        row["Id"],
        name=row["Name"].strip(),
        pos=(row["Latitude"], row["Longitude"])
    )

for _, row in edges.iterrows():
    G.add_edge(row["From"], row["To"], weight=row["Distance_m"])

# Create name → ID lookup (cleaned names)
name_to_id = {}

for _, row in nodes.iterrows():
    clean_name = clean(row["Name"])
    name_to_id[clean_name] = row["Id"]

# Ask user for building names
start_name = clean(input("Start building: "))
end_name = clean(input("Destination building: "))

# Check if buildings exist
if start_name not in name_to_id:
    print("❌ Start building not found.")
    print("Available buildings:")
    for n in nodes["Name"]:
        print("-", n.strip())
    exit()

if end_name not in name_to_id:
    print("❌ Destination building not found.")
    print("Available buildings:")
    for n in nodes["Name"]:
        print("-", n.strip())
    exit()

start = name_to_id[start_name]
end = name_to_id[end_name]

# Find shortest path
path = nx.shortest_path(G, start, end, weight="weight")

# Create map
first_node = nodes.iloc[0]
m = folium.Map(
    location=[first_node["Latitude"], first_node["Longitude"]],
    zoom_start=18
)

# Add markers
for _, row in nodes.iterrows():
    folium.Marker(
        [row["Latitude"], row["Longitude"]],
        popup=row["Name"].strip()
    ).add_to(m)

# Draw route
coords = []

for node in path:
    row = nodes[nodes["Id"] == node].iloc[0]
    coords.append((row["Latitude"], row["Longitude"]))

folium.PolyLine(coords, color="blue", weight=6).add_to(m)

# Save map
m.save("smart_campus_route.html")

print("✅ Route map saved as smart_campus_route.html")