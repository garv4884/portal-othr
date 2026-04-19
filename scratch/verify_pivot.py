import json
import db
import config

def test_expansion():
    print("--- Testing Expansion ---")
    gs = db.load_gs()
    MT = "ALPHA"
    gs["hp"][MT] = 5000
    gs["ap"][MT] = 1000
    gs["grid"][0] = MT # start
    gs["grid"][1] = "" # free adjacent
    db.save_gs(gs)
    
    ok, msg = db.expand_territory(gs, MT)
    print(f"Result: {ok}, Msg: {msg}")
    if ok:
        print(f"Grid[1] owner: {gs['grid'][1]}")
        print(f"AP remaining: {gs['ap'][MT]}")

def test_attack_queue():
    print("\n--- Testing Attack Queue ---")
    gs = db.load_gs()
    # Queue an attack: ALPHA hits CRIMSON 3 times
    gs["queued_actions"]["ALPHA"] = {"action": "ATTACK", "target": "CRIMSON", "hits": 3}
    gs["ap"]["ALPHA"] = 2000
    gs["hp"]["CRIMSON"] = 5000
    db.save_gs(gs)
    
    # Process epoch
    db.simulate_epoch(gs)
    
    new_gs = db.load_gs()
    print(f"CRIMSON HP: {new_gs['hp'].get('CRIMSON')}")
    if int(new_gs['hp'].get('CRIMSON')) == 4700:
        print("Success: 3 hits * 100 dmg = 300 hp reduction.")
    else:
        print(f"FAILED: HP reduction mismatch. Got {new_gs['hp'].get('CRIMSON')}")

if __name__ == "__main__":
    test_expansion()
    test_attack_queue()
