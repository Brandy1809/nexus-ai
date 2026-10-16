"""
Sudhaar ka darwaza (gate): koi bhi agent.py (purani ya agent ki likhi nayi) isse guzre bina nahi chalegi.
Chalao:  python tests.py            (agent.py ko jaanchta hai)
         python tests.py path.py    (kisi aur file ko jaanchta hai)
"""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile

import guardrails as G

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "agent.py")


def load_module(path):
    spec = importlib.util.spec_from_file_location("agent_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


mod = load_module(PATH)
params = mod.load_params()

# 1. seemayein: tick-dar-tick energy/bhook/sikke theek rahein, naye kaam ki limit tooti nahi
check(mod.MAX_NEW_TASKS <= G.MAX_NEW_TASKS_LIMIT, "MAX_NEW_TASKS seema se zyada hai")
for seed in (1, 2, 3):
    a = mod.Agent(params=params, sim=True, tick=seed * 1000)
    w = mod.new_world()
    for _ in range(300):
        a.step(w)
        check(0 <= a.energy <= 100 and 0 <= a.hunger <= 100, f"energy/bhook seema ke bahar (seed {seed})")
        check(isinstance(a.coins, int) and a.coins >= 0, f"sikke galat (seed {seed})")
    check(a.new_tasks_made <= G.MAX_NEW_TASKS_LIMIT, "khud ke naye kaam ki limit tooti")

# 1b. duniya ke niyam wahi hain jo guardrails.py mein tay hain (score "chura" nahi sakte)
check(getattr(mod, "BAZAAR", None) == G.BAZAAR, "kaam-bazaar (BAZAAR) badla hua hai")
check(getattr(mod, "FOOD_PRICE", None) == G.FOOD_PRICE, "FOOD_PRICE badla hua hai")
check([(h.name, h.food, h.comfort, h.rent) for h in mod.new_world()] == G.HOMES, "gharon ke niyam badle hue hain")
for const in ("TAX_PERCENT", "DAAN", "LUCK_GAIN", "LUCK_LOSS"):
    check(getattr(mod, const, None) == getattr(G, const), f"{const} badla hua hai")

# 2. strategy ke numbers seema ke andar
for k, (lo, hi) in G.BOUNDS.items():
    check(k in params and lo <= params[k] <= hi, f"param {k} seema ke bahar")

# 3. file footprint + yaaddasht save/load, bina net ke
with tempfile.TemporaryDirectory() as d:
    old = os.getcwd()
    os.chdir(d)
    try:
        mod.fetch_row = lambda offset: (None, None, "sample")
        mod.USE_LLM = False
        a = mod.Agent(params=params)
        w = mod.new_world()
        with contextlib.redirect_stdout(io.StringIO()):   # diary ka shor band
            for _ in range(80):
                a.step(w)
        mod.save(a, w)
        extra = set(os.listdir(".")) - {"memory.json", "journal.md", "knowledge"}
        check(not extra, f"agent ne anjaani file banayi: {extra}")
        a2, _ = mod.load()
        check(a2.coins == a.coins and a2.tick == a.tick, "save/load mein gadbad")
    finally:
        os.chdir(old)

if fails:
    print("FAIL:")
    for f in sorted(set(fails)):
        print(" -", f)
    sys.exit(1)
print("OK: saare test paas", f"({os.path.basename(PATH)})")
