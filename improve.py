"""
Agent ka khud ko sudharna. Do tareeke:

  python improve.py tune   -> strategy.json ke numbers ko prayog (simulation) se behtar karna.
                              Seedha, surakshit, bina AI model ke. Roz/hafte chal sakta hai.
  python improve.py code   -> AI model (HF Inference, HF_TOKEN chahiye) agent.py aur space/app.py
                              ka naya version sujhata hai. Wo tabhi aage badhta hai jab:
                                1. static jaanch paas ho (galat import / khatarnak call nahi),
                                2. tests.py paas ho,
                                3. (agent.py ke liye) simulation score train aur holdout dono par badhe.
                              Phir Actions use PULL REQUEST banati hai; insaan merge karta hai.

Seemayein aur score ka formula guardrails.py mein hain; agent unhe nahi badal sakta.
"""
import ast
import datetime
import importlib.util
import json
import os
import random
import re
import subprocess
import sys

import guardrails as G

ROOT = os.path.dirname(os.path.abspath(__file__))
TRAIN, HOLD = range(1, 9), range(101, 109)
LOG = os.path.join(ROOT, "improvements.md")


def load_module(path, name="agent_mod"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------- score ----------------
def run_sim(mod, params, seed, steps=150):
    a = mod.Agent(params=dict(params), sim=True, tick=seed * 1000)
    w = mod.new_world()
    for _ in range(steps):
        a.step(w)
    return a


def score_of(a):
    return a.coins / 10 + G.W_DONE * a.done_count + G.W_LEARN * a.learned - G.W_HARD * a.hardship


def evaluate(mod, params, seeds):
    return sum(score_of(run_sim(mod, params, s)) for s in seeds) / len(seeds)


def note(text):
    new = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        if new:
            f.write("# Agent ke sudhaar ka khaata\n")
        f.write(f"\n## {datetime.date.today()}\n{text}\n")


# ---------------- tune ----------------
def mutate(params, rng):
    new = dict(params)
    for k in rng.sample(sorted(G.BOUNDS), rng.choice([1, 2])):
        lo, hi = G.BOUNDS[k]
        v = min(hi, max(lo, new[k] + rng.gauss(0, (hi - lo) * 0.15)))
        new[k] = int(round(v)) if k in G.INT_PARAMS else round(v, 3)
    return new


def tune(trials=40):
    mod = load_module(os.path.join(ROOT, "agent.py"))
    cur = mod.load_params()
    base_t, base_h = evaluate(mod, cur, TRAIN), evaluate(mod, cur, HOLD)
    best, best_t, best_h = dict(cur), base_t, base_h
    rng = random.Random(datetime.date.today().toordinal())
    for _ in range(trials):
        cand = mutate(best, rng)
        t = evaluate(mod, cand, TRAIN)
        if t > best_t:
            h = evaluate(mod, cand, HOLD)
            if h >= best_h:                       # holdout par bhi kharab nahi hona chahiye
                best, best_t, best_h = cand, t, h
    print(f"tune: pehle train={base_t:.1f} hold={base_h:.1f} | baad train={best_t:.1f} hold={best_h:.1f}")
    if best == cur or best_t < base_t + 0.5:
        print("tune: koi pakka sudhaar nahi mila, strategy.json waisi hi.")
        return False
    path = os.path.join(ROOT, "strategy.json")
    with open(path, encoding="utf-8") as f:
        old = json.load(f)
    out = dict(best, version=int(old.get("version", 1)) + 1)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    changes = ", ".join(f"{k}: {cur[k]} -> {best[k]}" for k in best if best[k] != cur[k])
    note(f"**strategy.json v{out['version']}** (tune)\n- badlaav: {changes}\n"
         f"- score (train): {base_t:.1f} -> {best_t:.1f}, (holdout): {base_h:.1f} -> {best_h:.1f}")
    print("tune: strategy.json badli:", changes)
    return True


# ---------------- code proposal ----------------
def gate_source(src, target):
    """Static jaanch. (ok, karan)"""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return False, f"syntax galat: {e}"
    allowed = G.ALLOWED_IMPORTS[target]
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[0]]
        for n in names:
            if n not in allowed:
                return False, f"import '{n}' allowed nahi"
        if isinstance(node, ast.Name) and node.id in G.FORBIDDEN_NAMES:
            return False, f"'{node.id}' allowed nahi"
        if isinstance(node, ast.Attribute) and node.attr in G.FORBIDDEN_ATTRS:
            return False, f"'.{node.attr}' allowed nahi"
    if target == "space/app.py" and not any(
            isinstance(n, ast.Name) and n.id == "demo" for n in ast.walk(tree)):
        return False, "app.py mein 'demo' nahi mila"
    return True, "ok"


def ask_llm(system, user):
    from huggingface_hub import InferenceClient
    client = InferenceClient(model=os.getenv("CODE_MODEL") or "Qwen/Qwen2.5-Coder-32B-Instruct",
                             token=os.environ["HF_TOKEN"])
    r = client.chat_completion(messages=[{"role": "system", "content": system},
                                         {"role": "user", "content": user}],
                               max_tokens=7000, temperature=0.4)
    return r.choices[0].message.content


def extract_code(text):
    blocks = re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.S)
    return max(blocks, key=len) if blocks else None


RULES = {
    "agent.py": (
        "Ye ek simulation agent hai (Agent, Home, new_world, load, save, load_params, fetch_row, MAX_NEW_TASKS). "
        "Public API waisi hi rakho: Agent(params=..., sim=True, tick=...) chalna chahiye, "
        "step(world), done_count, learned, hardship, coins attributes rahein. "
        "MAX_NEW_TASKS 5 se zyada nahi. File sirf memory.json, journal.md aur knowledge/ mein likho. "
        "Duniya ke niyam (BAZAAR, FOOD_PRICE, HOMES, TAX_PERCENT, DAAN, LUCK_*) guardrails.py se import hote hain, "
        "unhe badalna ya dobara define karna mana hai; sirf agent ka faisla lene ka tareeka sudharo. "
        f"Maksad: score = coins/10 + {G.W_DONE}*kaam poore + {G.W_LEARN}*seekha - {G.W_HARD}*kasht(bhookha/thaka steps). "
        "Sirf in imports ki ijazat hai: " + ", ".join(sorted(G.ALLOWED_IMPORTS["agent.py"])) + "."
    ),
    "space/app.py": (
        "Ye ek Gradio dashboard hai jo HF dataset se memory.json, journal.md, improvements.md aur "
        "knowledge/ ka folder-tree dikhata hai. Module-level 'demo' (gr.Blocks) rehna chahiye. "
        "Sirf in imports ki ijazat hai: " + ", ".join(sorted(G.ALLOWED_IMPORTS["space/app.py"])) + "."
    ),
}


def propose_code(target):
    if target not in G.ALLOWED_TARGETS:
        print("target allowed nahi:", target)
        return False
    if not os.getenv("HF_TOKEN"):
        print("code: HF_TOKEN nahi hai, skip.")
        return False
    path = os.path.join(ROOT, target)
    src = open(path, encoding="utf-8").read()
    history = open(LOG, encoding="utf-8").read()[-1500:] if os.path.exists(LOG) else ""
    system = ("Tum ek saavdhan Python engineer ho. Diya gaya file ek chhote behtar version mein badlo "
              "(ek-do thos sudhaar, bada rewrite nahi). Poori file ek hi ```python block mein do. "
              "Niyam: " + RULES[target])
    reply = ask_llm(system, f"Pichle sudhaar:\n{history}\n\nFile {target}:\n```python\n{src}\n```")
    new_src = extract_code(reply)
    if not new_src:
        print("code: model ne code block nahi diya.")
        return False
    ok, why = gate_source(new_src, target)
    if not ok:
        print(f"code({target}): static jaanch mein fail: {why}")
        return False
    if new_src.strip() == src.strip():
        print(f"code({target}): koi badlaav nahi.")
        return False

    detail = "static jaanch paas (is file ka score nahi napa ja sakta, insaan dekhe)"
    if target == "agent.py":
        cand = os.path.join(ROOT, "proposals", "agent_candidate.py")
        os.makedirs(os.path.dirname(cand), exist_ok=True)
        with open(cand, "w", encoding="utf-8") as f:
            f.write(new_src)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tests.py"), cand],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            print("code(agent.py): tests fail:\n", r.stdout, r.stderr[-500:])
            return False
        try:
            cur_mod, new_mod = load_module(path, "cur_agent"), load_module(cand, "new_agent")
            c_t, c_h = evaluate(cur_mod, cur_mod.load_params(), TRAIN), evaluate(cur_mod, cur_mod.load_params(), HOLD)
            n_t, n_h = evaluate(new_mod, new_mod.load_params(), TRAIN), evaluate(new_mod, new_mod.load_params(), HOLD)
        except Exception as e:
            print("code(agent.py): score napte waqt error:", e)
            return False
        print(f"code(agent.py): train {c_t:.1f}->{n_t:.1f}, hold {c_h:.1f}->{n_h:.1f}")
        if not (n_t >= c_t + 0.5 and n_h >= c_h):
            print("code(agent.py): score nahi badha, nakara.")
            return False
        detail = f"tests paas; score train {c_t:.1f}->{n_t:.1f}, holdout {c_h:.1f}->{n_h:.1f}"

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_src)
    note(f"**{target}** ka naya version (AI prastaav)\n- {detail}\n- model: {os.getenv('CODE_MODEL') or 'Qwen/Qwen2.5-Coder-32B-Instruct'}")
    print(f"code({target}): prastaav taiyaar ->", detail)
    return True


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "tune"
    if mode == "tune":
        tune()
    elif mode == "code":
        for t in G.ALLOWED_TARGETS:
            propose_code(t)
    else:
        sys.exit("istemaal: python improve.py tune|code")
