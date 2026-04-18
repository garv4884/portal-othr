import math
from scipy.spatial import Delaunay

def generate_amoeba_points(n=30, width=600, height=500):
    points = []
    phi = (1 + math.sqrt(5)) / 2
    for i in range(n):
        r = 200 * math.sqrt((i + 0.5) / n)
        theta = 2 * math.pi * i / phi
        noiseX = math.sin(i * 123) * 15
        noiseY = math.cos(i * 321) * 15
        x = width / 2 + r * math.cos(theta) + noiseX
        y = height / 2 + r * math.sin(theta) + noiseY
        points.append((x, y))
    return points

def get_amoeba_adjacency(n=30):
    points = generate_amoeba_points(n)
    tri = Delaunay(points)
    adj = {i: set() for i in range(n)}
    for simplex in tri.simplices:
        adj[simplex[0]].update([simplex[1], simplex[2]])
        adj[simplex[1]].update([simplex[0], simplex[2]])
        adj[simplex[2]].update([simplex[0], simplex[1]])
    return {k: sorted(list(v)) for k, v in adj.items()}

adj = get_amoeba_adjacency(30)
print(adj)
