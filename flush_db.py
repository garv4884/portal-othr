"""
OVERTHRONE :: flush_db.py
One-shot script to reset the Upstash Redis database.
Run: python flush_db.py <REDIS_URL>
"""
import sys
import redis
import json

if len(sys.argv) < 2:
    print("Usage: python flush_db.py <REDIS_URL>")
    print("Example: python flush_db.py rediss://default:xxxx@your-db.upstash.io:6380")
    sys.exit(1)

url = sys.argv[1]
R = redis.from_url(url, decode_responses=True)

print("Connected to Redis. Current keys:")
# List game keys
keys = ["ot:teams_meta", "ot:state", "ot:events", "ot:users"]
for k in keys:
    val = R.get(k)
    if val:
        print(f"  {k}: {len(val)} bytes")
    else:
        print(f"  {k}: (empty)")

print()
print("Choose reset mode:")
print("  1) Delete teams + game state only (keep user accounts)")
print("  2) Flush ENTIRE database (everyone must re-register)")
choice = input("Enter 1 or 2: ").strip()

if choice == "1":
    R.delete("ot:teams_meta")
    R.delete("ot:state")
    R.delete("ot:events")
    # Clear team field on all users
    raw = R.get("ot:users")
    if raw:
        users = json.loads(raw)
        for u in users.values():
            u["team"] = None
        R.set("ot:users", json.dumps(users))
    print("✅ Teams and game state wiped. User accounts preserved.")

elif choice == "2":
    confirm = input("Type YES to confirm full flush: ").strip()
    if confirm == "YES":
        R.flushdb()
        print("✅ Database fully flushed.")
    else:
        print("Aborted.")
else:
    print("Invalid choice. Aborted.")
