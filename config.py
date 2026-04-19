"""
OVERTHRONE :: config.py
Grid map configurations and constants.
"""

STARTING_HP = 5000
STARTING_AP = 1200
EPOCH_DURATION_SECS = 300  # 5 minutes
ATTACK_COST_AP = 500
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
        {"id":"h1","title":"Historian's Message","diff":"EASY","pts":500,"desc":"A historian left behind a message, but spacing and punctuation were erased by time: Qlk_vhgl_vw_ylvlel. Can you restore its meaning?"},
        {"id":"h2","title":"Ancient Broadcast","diff":"EASY","pts":500,"desc":"This broadcast was captured decades ago. Download the audio file to decode it.","link":"https://drive.google.com/file/d/1OUG1uTlha1qPLVE3uS4v9Z2fz9mMck0i/view?usp=sharing"},
        {"id":"h3","title":"Hex Color Code","diff":"EASY","pts":500,"desc":"Which color is #0502FA?"},
        {"id":"h4","title":"Secret Cipher","diff":"EASY","pts":500,"desc":"Encrypt: CAT (A→B, B→C...)"},
        {"id":"h5","title":"Broken Transmission","diff":"EASY","pts":500,"desc":"Decrypt: Eudnh_wkh_frgh_iluvw (Shift 3 forward)."},
        {"id":"h6","title":"Binary Message","diff":"EASY","pts":500,"desc":"Convert: 01101100 01101111 01100111 01101001 01101110 01011111 01101110 01101111 01110111."},
        {"id":"h7","title":"XOR Mystery","diff":"EASY","pts":500,"desc":"Find the XOR of all numbers from 1 to 10."},
        {"id":"h8","title":"String Collapse","diff":"EASY","pts":500,"desc":"Collapse 'ttiiiiieeeeiieett' by removing groups of ≥3 consecutive chars."},
        {"id":"h9","title":"Bit Flip Score","diff":"EASY","pts":500,"desc":"Binary: 11010011101101001110. Flip one contiguous subarray. Max 1s?"},
        {"id":"h10","title":"Subsequence Illusion","diff":"EASY","pts":500,"desc":"Count distinct subsequences of 'istetiet' equal to 'tiet'."},
        {"id":"h11","title":"Audio Archive","diff":"MEDIUM","pts":750,"desc":"Analyze the static for hidden messages.","link":"https://drive.google.com/file/d/1WEEu48om3dtKn0rHF9kWaDxkVeCtwauk/view?usp=drive_link"},
        {"id":"h12","title":"Hex Decode","diff":"MEDIUM","pts":750,"desc":"Decode: 73 65 63 72 65 74 5f 62 61 73 65."},
        {"id":"h13","title":"Git History","diff":"MEDIUM","pts":750,"desc":"Retrieve the secret from the repository's past.","link":"https://drive.google.com/file/d/1yYNGltWlgc7v3b7ggvhwELHuJVQKl0n9/view?usp=drive_link"},
        {"id":"h14","title":"Corrupted Image","diff":"MEDIUM","pts":750,"desc":"Analyze layers of image security.","link":"https://drive.google.com/file/d/1x65T0p9l0TNbtpcck1CAWSRceIOhrOaH/view?usp=drive_link"},
        {"id":"h15","title":"Obfuscated JavaScript","diff":"MEDIUM","pts":750,"desc":"Deobfuscate the logic behind the simple transformation.","link":"https://drive.google.com/file/d/1jeqcox0Zmf3xsBO26fCiT_ZTz4hXUr9b/view?usp=drive_link"},
        {"id":"h16","title":"PDF Secrets","diff":"MEDIUM","pts":750,"desc":"Analyze the PDF for hidden object data.","link":"https://drive.google.com/file/d/1FblfNeNq6hUvhjc2o0-Oo9yjdZox2MCa/view?usp=drive_link"},
        {"id":"h17","title":"ZIP Comments","diff":"MEDIUM","pts":750,"desc":"Find the flag hidden in the archive metadata.","link":"https://drive.google.com/file/d/1ii_d1yvkzkJyEYRBjMOxCR-Bg51XQLav/view?usp=drive_link"},
        {"id":"h18","title":"Grid Pathfinding","diff":"MEDIUM","pts":750,"desc":"Min path sum in [[1,3,1],[1,5,1],[4,2,1]]."},
        {"id":"h19","title":"Elevator Puzzle","diff":"MEDIUM","pts":750,"desc":"Complex floor calculation starting at floor 10."},
        {"id":"h20","title":"Heartbeat Signal","diff":"MEDIUM","pts":750,"desc":"Analyze ICMP packet capture for hidden data.","link":"https://drive.google.com/file/d/1X3h8Da3pBE78r6FRAxrz6HRiNk77S9RD/view?usp=drive_link"},
        {"id":"h21","title":"Triple Encryption","diff":"HARD","pts":1000,"desc":"Reverse XOR -> ROT13 -> Hex Process."},
        {"id":"h22","title":"Baby RSA","diff":"HARD","pts":1000,"desc":"n=3233, e=17, c=2790. Solve for single ASCII char."},
        {"id":"h23","title":"Sudoku Solver","diff":"HARD","pts":1000,"desc":"Sum the main diagonal digits of the solved grid."},
        {"id":"h24","title":"Protocol Tunnel","diff":"HARD","pts":1000,"desc":"Analyze firewall logs for header tunneling.","link":"https://drive.google.com/file/d/1NMNPh4PchneqFKFCVWUiwmnEYvzY9KLw/view?usp=drive_link"},
        {"id":"h25","title":"Chromatic Vault","diff":"HARD","pts":1000,"desc":"Analyze pixel palette poisoning.","link":"https://drive.google.com/file/d/1OISMonvwopLFBF1lRpHx7yEcivwhJgwW/view?usp=drive_link"},
        {"id":"h26","title":"Packet Sniffer","diff":"HARD","pts":1000,"desc":"Reconstruct the file from the packet stream.","link":"https://drive.google.com/file/d/16tY-j-q0ywwb8ipJA8cu42q9_hoUdgrX/view?usp=drive_link"},
        {"id":"h27","title":"Ghost in Crontab","diff":"HARD","pts":1000,"desc":"Decode the schedule-based flag.","link":"https://drive.google.com/file/d/1eN5Kc7vrBgYURrd7SiA3n1ShWVVoKZyK/view?usp=drive_link"},
    ],
}

MONARCH_TASK_PORTAL = {
    "h1": {"answer": "old_things_still_work"},
    "h2": {"answer": "fr3qu3ncy_m4tt3rs"},
    "h3": {"answer": "Bright Electric Blue"},
    "h4": {"answer": "DBU"},
    "h5": {"answer": "Break_the_code_first"},
    "h6": {"answer": "login_now"},
    "h7": {"answer": "11"},
    "h8": {"answer": "tiet"},
    "h9": {"answer": "14"},
    "h10": {"answer": "2"},
    "h11": {"answer": "v1su4l_v1brati0ns"},
    "h12": {"answer": "secret_base"},
    "h13": {"answer": "git_n3v3r_forg3ts"},
    "h14": {"answer": "n3st3d_m4tr3ry0shka_d0ll"},
    "h15": {"answer": "js_0bfusc4t10n_1s_4rt_2026"},
    "h16": {"answer": "p1df_0bj3ct_h1d3_2026"},
    "h17": {"answer": "z1p_c0mm3nt_n0t_s0_s3cr3t_2026"},
    "h18": {"answer": "7"},
    "h19": {"answer": "2"},
    "h20": {"answer": "p1ng_p0ng_d4t4_42"},
    "h21": {"answer": "you_will_never"},
    "h22": {"answer": "A"},
    "h23": {"answer": "47"},
    "h24": {"answer": "p1ng_p0ng_pr0t0c0l"},
    "h25": {"answer": "p4l3tt3_p01s0n1ng_4281"},
    "h26": {"answer": "p4ck3t_h4ck3r_n01_2026"},
    "h27": {"answer": "cr0n_j0b_h3r0_2026"},
}

BOT_TASKS = {
    "NA_06": {
        "id":"NA_06", "category":"Neural Architect", "title":"Convolution Engine",
        "description":"Apply 3x3 convolution to a 10x10 grid with padding=1",
        "difficulty":"MEDIUM", "ap_reward":750, "function_name":"convolution_3x3",
        "template":"def convolution_3x3(grid, kernel):\n    return [[0]*10 for _ in range(10)]",
        "test_harness":"grid = [[1.0]*10 for _ in range(10)]\nkernel = [[1/9]*3 for _ in range(3)]\nresult = convolution_3x3(grid, kernel)\nverify_val = round(result[5][5], 1)",
        "expected_output": 1.0,
        "verify_token":"CONV_RESULT"
    },
    "CB_06": {
        "id":"CB_06", "category":"Cipher Breaker", "title":"Vigenère Decryption",
        "description":"Decrypt Vigenère cipher given key.",
        "difficulty":"HARD", "ap_reward":1000, "function_name":"decrypt_vigenere",
        "template":"def decrypt_vigenere(ciphertext, key):\n    return ''",
        "test_harness":"ciphertext = 'LXFOPVEFRNHR'\nkey = 'KEY'\nresult = decrypt_vigenere(ciphertext, key)\nverify_val = result.upper()",
        "expected_output": "ATTACKATDAWN",
        "verify_token":"VIG_DECRYPTED"
    },
    # (Truncated for brevity, but all tasks from cooked config.py would be here)
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
        r = 180 * math.sqrt((i+0.5)/n)
        theta = 2 * math.pi * i / phi
        noiseX = (math.sin(i*123) * 15)
        noiseY = (math.cos(i*321) * 15)
        points.append((width/2 + r * math.cos(theta) + noiseX, height/2 + r * math.sin(theta) + noiseY))
    return points

def get_amoeba_adjacency(n=30):
    from scipy.spatial import Delaunay
    points = generate_amoeba_points(n)
    tri = Delaunay(points)
    adj = {i: set() for i in range(n)}
    for s in tri.simplices:
        adj[s[0]].update([s[1], s[2]])
        adj[s[1]].update([s[0], s[2]])
        adj[s[2]].update([s[0], s[1]])
    return {k: list(v) for k, v in adj.items()}
