"""
OVERTHRONE :: config.py
Grid map configurations and constants.
"""

STARTING_HP = 5000
STARTING_AP = 1200
EPOCH_DURATION_SECS = 900  # 15 minutes
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
        {"id":"m1","title":"Cipher of Seven Seals",    "diff":"EASY",   "pts":500,  "desc":"Decode a Caesar-13 shift applied to the royal decree.", "link":"https://www.google.com/search?q=caesar+cipher", "flag":"HELIX{C4ES4R}"},
        {"id":"m2","title":"The Merchant's Paradox",   "diff":"MEDIUM", "pts":750,  "desc":"Solve the riddle: which merchant owes the crown gold?", "link":"https://www.google.com/search?q=paradox", "flag":"HELIX{M3RCH4NT}"},
        {"id":"m3","title":"Labyrinth of Mirrors",     "diff":"MEDIUM", "pts":750,  "desc":"Navigate the logic grid — only one path leads to the throne.", "link":"https://www.google.com/search?q=labyrinth", "flag":"HELIX{M1RR0R5}"},
        {"id":"m4","title":"The Dragon's Number",      "diff":"HARD",   "pts":1000, "desc":"Find the prime p where p^2 - p + 41 is also prime, beyond p=40.", "link":"https://www.google.com/search?q=prime+math", "flag":"HELIX{PR1M3_41}"},
    ],
    "sovereign": [
        {"id":"s1","title":"Fibonacci Engine",    "diff":"EASY",   "pts":500,  "desc":"Write a function that computes and prints the 20th Fibonacci number (where F(0)=0, F(1)=1).",
         "starter": "def fib(n):\n    # Your code here\n    pass\n\nprint(fib(20))", "verify": "6765"},
        {"id":"s2","title":"Prime Factorization Engine",    "diff":"MEDIUM", "pts":750,  "desc":"Compute and print the largest prime factor of the number 315.",
         "starter": "def largest_prime_factor(n):\n    # Your code here\n    pass\n\nprint(largest_prime_factor(315))", "verify": "7"},
        {"id":"s3","title":"Territory Score Calc",     "diff":"MEDIUM", "pts":750,  "desc":"Compute a frequency dictionary for a map grid: ['A','A','C','','V','V','V']",
         "starter": "def compute_scores(grid):\n    # Your code here\n    pass\n\ngrid = ['A','A','C','',  'V','V','V']\nprint(compute_scores(grid))", "verify": "{'A': 2, 'C': 1, 'V': 3}"},
        {"id":"s4","title":"Sovereign Trajectory","diff":"HARD",   "pts":1000, "desc":"A bot starts at (0,0). Orders: 'UUDDLRLRBA'. U=(0,1), D=(0,-1), L=(-1,0), R=(1,0), others ignored. Print final (X,Y) as a tuple.",
         "starter": "def trace_path(moves):\n    x,y = 0,0\n    # Your code here\n    pass\n\nprint(trace_path('UUDDLRLRBA'))", "verify": "(0, 0)"},
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
        # Phyllotaxis Spiral (matches D3 frontend logic)
        r = 180 * math.sqrt((i + 0.5) / n)
        theta = 2 * math.pi * i / phi
        noiseX = math.sin(i * 123) * 15
        noiseY = math.cos(i * 321) * 15
        x = width / 2 + r * math.cos(theta) + noiseX
        y = height / 2 + r * math.sin(theta) + noiseY
        points.append((x, y))
    return points

def get_amoeba_adjacency(n=30):
    """Dynamically generates a nearest-neighbor mesh for n points."""
    points = generate_amoeba_points(n)
    adj = {i: [] for i in range(n)}
    
    for i in range(n):
        x1, y1 = points[i]
        dists = []
        for j in range(n):
            if i == j: continue
            x2, y2 = points[j]
            dists.append((j, (x1-x2)**2 + (y1-y2)**2))
        
        # Connect to 6 nearest neighbors for a robust organic mesh
        dists.sort(key=lambda x: x[1])
        for neighbor_idx, _ in dists[:6]: 
            adj[i].append(neighbor_idx)
            
    return adj
