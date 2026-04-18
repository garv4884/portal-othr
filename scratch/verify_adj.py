from config import get_amoeba_adjacency

adj = get_amoeba_adjacency(30)
print(f"Adjacency for 30 cells: {len(adj)} entries")
print(f"Cell 0 neighbors: {adj[0]}")
assert len(adj) == 30
assert 1 in adj[0]
print("Verification SUCCESSFUL")
