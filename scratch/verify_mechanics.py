import json
import time
import sys
from datetime import datetime, timedelta

# Mock streamlit secrets for local Redis access if needed
# (Assuming R is already connected in db.py)
import db
import config

def test_blitz():
    print("--- Testing Blitz ---")
    gs = db.load_gs()
    MT = "ALPHA"
    target = 5 # arbitrary
    
    # Setup test state
    gs["ap"][MT] = 1000
    gs["grid"][0] = MT # ensure adjacency
    
    # We need to mock adjacency logic from config
    adj = config.get_amoeba_adjacency(len(gs["grid"]))
    is_adj = target in adj.get(0, [])
    print(f"Cell {target} adjacent to 0: {is_adj}")
    
    if is_adj and gs["ap"][MT] >= config.ATTACK_COST_AP:
        gs["grid"][target] = MT
        gs["ap"][MT] -= config.ATTACK_COST_AP
        db.save_gs(gs)
        print("Blitz Success!")
    else:
        print("Blitz Logic Failed or Not Adjacent.")

def test_alliances():
    print("\n--- Testing Alliance Rewards ---")
    gs = db.load_gs()
    gs["alliances"] = {"ALPHA": ["CRIMSON"], "CRIMSON": ["ALPHA"]}
    gs["ap"]["ALPHA"] = 0
    gs["ap"]["CRIMSON"] = 0
    gs["hp"]["ALPHA"] = 5000
    gs["hp"]["CRIMSON"] = 5000
    db.save_gs(gs)
    
    db.apply_task_rewards(gs, "ALPHA", 500, "Test Operation")
    db.save_gs(gs)
    
    new_gs = db.load_gs()
    print(f"ALPHA AP: {new_gs['ap']['ALPHA']}")
    print(f"CRIMSON AP: {new_gs['ap']['CRIMSON']}")
    if new_gs['ap']['CRIMSON'] == 500:
        print("Alliance sharing success!")
    else:
        print("Alliance sharing FAILED.")

def test_heuristic_bot():
    print("\n--- Testing Heuristic Bot ---")
    gs = db.load_gs()
    # Define a bot that prefers empty cells
    gs["bots"] = {
        "ALPHA": 'def evaluate_target(target):\n    return 100 if target["is_empty"] else 0'
    }
    gs["ap"]["ALPHA"] = 1000
    gs["grid"][0] = "ALPHA" # starting point
    gs["grid"][1] = "" # empty neighbor
    db.save_gs(gs)
    
    # Run simulation
    db.simulate_epoch(gs)
    
    new_gs = db.load_gs()
    if new_gs["grid"][1] == "ALPHA":
        print("Bot attack success!")
    else:
        print("Bot attack FAILED.")

if __name__ == "__main__":
    test_blitz()
    test_alliances()
    test_heuristic_bot()
