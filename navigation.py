import pandas as pd
import networkx as nx

# Load data
nodes = pd.read_excel("Nodes_sheet - 1.xlsx", sheet_name="Nodes")
edges = pd.read_excel("Edges_with_distance.xlsx")

# Clean data
nodes = nodes.dropna(subset=["Id"])
edges = edges.dropna(subset=["From", "To", "Distance_m"])

nodes["Id"] = nodes["Id"].astype(int)
edges["From"] = edges["From"].astype(int)
edges["To"] = edges["To"].astype(int)

# Create graph
G = nx.Graph()

# Add nodes
for _, row in nodes.iterrows():
    G.add_node(row["Id"], name=row["Name"])

# Add edges with distance
for _, row in edges.iterrows():
    G.add_edge(row["From"], row["To"], weight=row["Distance_m"])

# Ask user for start and destination
start = int(input("Enter start node ID: "))
end = int(input("Enter destination node ID: "))

# Calculate shortest path
path = nx.shortest_path(G, start, end, weight="weight")
distance = nx.shortest_path_length(G, start, end, weight="weight")

print("\nBest route:")
for node in path:
    name = nodes[nodes["Id"] == node]["Name"].values[0]
    print(name)

print(f"\nTotal distance: {distance:.2f} meters")