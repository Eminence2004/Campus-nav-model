import pandas as pd
from geopy.distance import geodesic

# Load Excel file
file = "Nodes_sheet - 1.xlsx"

nodes = pd.read_excel(file, sheet_name="Nodes")
edges = pd.read_excel(file, sheet_name="Edges")

# Remove empty rows
nodes = nodes.dropna(subset=["Id", "Latitude", "Longitude"])
edges = edges.dropna(subset=["From", "To"])

# Convert IDs to integers
nodes["Id"] = nodes["Id"].astype(int)
edges["From"] = edges["From"].astype(int)
edges["To"] = edges["To"].astype(int)

# Function to get coordinates of a node
def get_coord(node_id):
    row = nodes[nodes["Id"] == node_id]
    
    if row.empty:
        print(f"Warning: Node {node_id} not found")
        return None
    
    row = row.iloc[0]
    return (row["Latitude"], row["Longitude"])

distances = []

# Calculate distances
for _, edge in edges.iterrows():
    
    p1 = get_coord(edge["From"])
    p2 = get_coord(edge["To"])

    if p1 and p2:
        d = geodesic(p1, p2).meters
    else:
        d = None

    distances.append(d)

edges["Distance_m"] = distances

# Save result
edges.to_excel("Edges_with_distance.xlsx", index=False)

print("✅ Distances calculated and saved to Edges_with_distance.xlsx")