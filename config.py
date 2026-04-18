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

# Team Configuration
TEAM_COLORS = {
    "ALPHA":   {"color": "#0099FF", "bg": "#001933", "icon": "🔵"},
    "CRIMSON": {"color": "#FF2244", "bg": "#330011", "icon": "🔴"},
    "VERDANT": {"color": "#00CC88", "bg": "#003322", "icon": "🟢"},
    "AURUM":   {"color": "#FFB800", "bg": "#332500", "icon": "🟡"},
    "MYSTIC":  {"color": "#CC44FF", "bg": "#220033", "icon": "🟣"},
    "EMBER":   {"color": "#FF8800", "bg": "#331100", "icon": "🟠"},
}

# Alias for compatibility if needed
TEAM_PALETTE = list(TEAM_COLORS.values())

# Action Cards Configuration
ACTION_CARDS = [
    {
        "id": "ATTACK",
        "icon": "🗡️",
        "label": "BLITZ ATTACK",
        "desc": "Seize a random enemy cell. High risk, immediate reward.",
        "cost": 500,
        "color": "#FF2244"
    },
    {
        "id": "ALLIANCE",
        "icon": "🤝",
        "label": "DIPLOMATIC PACT",
        "desc": "Declare non-aggression. Publicly marks another team as an ally.",
        "cost": 0,
        "color": "#00CC88"
    },
    {
        "id": "BACKSTAB",
        "icon": "🗡️",
        "label": "TREACHEROUS STRIKE",
        "desc": "Massive damage to an ally's territory. High HP drain.",
        "cost": 1500,
        "color": "#9933FF"
    },
    {
        "id": "SUSPICION",
        "icon": "👁️",
        "label": "ACCUSE TRAITOR",
        "desc": "Expose a plotter. If correct, they suffer massive damage.",
        "cost": 1000,
        "color": "#FFB800"
    }
]

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

AMO_ADJ = {0: [1, 2, 3, 4, 5, 8], 1: [0, 3, 4, 6, 9], 2: [0, 4, 5, 7, 10, 15], 3: [0, 1, 6, 8, 11], 4: [0, 1, 2, 7, 9, 12, 17], 5: [0, 2, 8, 10, 13, 18], 6: [1, 3, 9, 11, 14, 19], 7: [2, 4, 12, 15, 20], 8: [0, 3, 5, 11, 13, 16, 21, 29], 9: [1, 4, 6, 14, 17, 22], 10: [2, 5, 15, 18, 23], 11: [3, 6, 8, 16, 19, 24], 12: [4, 7, 17, 20, 25], 13: [5, 8, 18, 21, 26], 14: [6, 9, 19, 22, 27], 15: [2, 7, 10, 20, 23, 28], 16: [8, 11, 24, 29], 17: [4, 9, 12, 22, 25], 18: [5, 10, 13, 23, 26], 19: [6, 11, 14, 24, 27], 20: [7, 12, 15, 25, 28], 21: [8, 13, 26, 29], 22: [9, 14, 17, 27], 23: [10, 15, 18, 26, 28], 24: [11, 16, 19, 27, 29], 25: [12, 17, 20], 26: [13, 18, 21, 23], 27: [14, 19, 22, 24], 28: [15, 20, 23], 29: [8, 16, 21, 24]}

def get_amoeba_adjacency(n=30):
    return {k: v for k, v in AMO_ADJ.items() if k < n}
