"""
OVERTHRONE :: config.py
Grid map configurations and constants.
"""

STARTING_HP = 5000
STARTING_AP = 1200
EPOCH_DURATION_SECS = 300  # 5 minutes
ATTACK_COST_AP = 500
TASK_COOLDOWN_SECS = 900
TASK_FAIL_CHANCE = 0.15

# Color Palettes
TEAM_PALETTE = [
    {"color": "#0099FF", "bg": "#001933", "icon": "🔵"},
    {"color": "#FF2244", "bg": "#330011", "icon": "🔴"},
    {"color": "#00CC88", "bg": "#003322", "icon": "🟢"},
    {"color": "#FFB800", "bg": "#332500", "icon": "🟡"},
    {"color": "#CC44FF", "bg": "#220033", "icon": "🟣"},
    {"color": "#FF8800", "bg": "#331100", "icon": "🟠"},
]

CELL_COLORS = {
    "ALPHA": "#0a2040", "CRIMSON": "#2a0a0a", "VERDANT": "#0a2a12", "AURUM": "#2a1a00", 
    "NONE": "#0a1a0e" # default free
}
CELL_GLOW = {
    "ALPHA": "#0099FF", "CRIMSON": "#FF2244", "VERDANT": "#00CC88", "AURUM": "#FFB800",
    "NONE": "transparent"
}

# PUBG-style terrain special cells
TERRAIN_SPECIAL = {15: "🪂", 44: "💊", 55: "🔫", 33: "🏥", 66: "💣"}

TASKS = {
    "monarch": [
        {"id":"m1","title":"Cipher of Seven Seals",    "diff":"EASY",   "pts":500,  "desc":"Decode a Caesar-13 shift applied to the royal decree."},
        {"id":"m2","title":"The Merchant's Paradox",   "diff":"MEDIUM", "pts":750,  "desc":"Solve the riddle: which merchant owes the crown gold?"},
        {"id":"m3","title":"Labyrinth of Mirrors",     "diff":"MEDIUM", "pts":750,  "desc":"Navigate the logic grid — only one path leads to the throne."},
        {"id":"m4","title":"The Dragon's Number",      "diff":"HARD",   "pts":1000, "desc":"Find the prime p where p^2 - p + 41 is also prime, beyond p=40."},
    ],
    "sovereign": [
        {"id":"s1","title":"API Backoff Optimizer",    "diff":"EASY",   "pts":500,  "desc":"Implement exponential backoff with jitter for HTTP retries.",
         "starter": "import time, random\n\ndef backoff_retry(max_retries=5):\n    for attempt in range(max_retries):\n        # Your code here\n        pass\n\nbackoff_retry()"},
        {"id":"s2","title":"BFS Territory Scanner",    "diff":"MEDIUM", "pts":750,  "desc":"Write BFS to find all cells reachable within N moves on a 10x10 grid.",
         "starter": "from collections import deque\n\ndef bfs_reachable(start, n, grid_size=10):\n    # Your BFS implementation here\n    visited = set()\n    queue = deque([(start, 0)])\n    # ...\n    return visited\n\nprint(bfs_reachable(0, 3))"},
        {"id":"s3","title":"Territory Score Calc",     "diff":"MEDIUM", "pts":750,  "desc":"Write a function to compute team scores from a grid list.",
         "starter": "def compute_scores(grid):\n    scores = {}\n    for cell in grid:\n        if cell:\n            scores[cell] = scores.get(cell, 0) + 1\n    return scores\n\ngrid = ['ALPHA','ALPHA','CRIMSON','',  'VERDANT']\nprint(compute_scores(grid))"},
        {"id":"s4","title":"Sovereign Strategy Engine","diff":"HARD",   "pts":1000, "desc":"Code a greedy+lookahead function to maximize territory gain.",
         "starter": "def best_attack(my_cells, enemy_grid):\n    # Greedy strategy: find most isolated enemy cell\n    # Return index of best cell to capture\n    pass\n\nprint(best_attack([0,1,10], ['CRIMSON']*100))"},
    ],
}

DIFF_COLOR = {"EASY": "#00CC88", "MEDIUM": "#FFB800", "HARD": "#FF2244"}
EVENT_COLORS = {
    "ATTACK":"#FF2244","BACKSTAB":"#9933FF","ALLIANCE":"#00CC88",
    "SUSPICION":"#FFB800","TASK":"#00E5FF","SYS":"#3a3a5a","WS_TX":"#00CC88",
}

import math

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
    from scipy.spatial import Delaunay
    points = generate_amoeba_points(n)
    tri = Delaunay(points)
    adj = {i: set() for i in range(n)}
    for simplex in tri.simplices:
        adj[simplex[0]].update([simplex[1], simplex[2]])
        adj[simplex[1]].update([simplex[0], simplex[2]])
        adj[simplex[2]].update([simplex[0], simplex[1]])
    return {k: list(v) for k, v in adj.items()}
