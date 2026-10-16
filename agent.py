"""
Nexus v2: ghar, dimaag, paisa, safar, yaaddasht aur khud ko sudharna.

DIMAAG (upar se neeche = zyada zaroori; thresholds strategy.json se aate hain):
  1. THAKAAN  -> energy kam to SO JAO
  2. BHOOK    -> khana ghar mein hai to khao, nahi to kharido, paise nahi to kaam/naya ghar
  3. TASK     -> koi kaam hai to karo
  4. JIGYASA  -> kaam nahi bacha: kaam-bazaar se lo, ya khud naya kaam banao, ya ghoomo, ya joke

SAMAJ: garib (<30 sikke), madhyam (<100), amir (100+). Raja har 10 step par amir se 10% kar
leta hai, garib ko 10 sikke daan deta hai, aur har ghar mein 1 khana ugta hai.

SAFAR: Hugging Face dataset ki asli rows. Jo seekhta hai wo topic/subtopic/mahina folder mein
save hota hai (knowledge/<topic>/<subtopic>/<YYYY-MM>/<id>.json) aur HF dataset par jata hai.

SUDHAAR: improve.py strategy.json ke numbers ko prayog se behtar karta hai (ye file nahi badalta,
sirf dimaag ke numbers). Seemayein guardrails.py mein hain.
"""
import datetime
import hashlib
import json
import os
import random
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from guardrails import (BAZAAR, BOUNDS, DAAN, FOOD_PRICE, HOMES, INT_PARAMS, LUCK_GAIN,
                        LUCK_LOSS, MAX_NEW_TASKS_LIMIT, TAX_PERCENT)


def env(name, default):
    return os.getenv(name) or default


DATASET = env("HF_DATASET", "fancyzhx/ag_news")      # safar ki duniya
USE_LLM = env("USE_LLM", "0") == "1"                 # sochne wala open-source model
LLM_MODEL = env("LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
STEPS = int(env("STEPS", "40"))
MAX_NEW_TASKS = 5
MEMORY, JOURNAL = "memory.json", "journal.md"
KNOWLEDGE_DIR, STRATEGY_FILE = "knowledge", "strategy.json"

DEFAULT_PARAMS = {"sleep_below": 20, "eat_above": 70, "madhyam_job_chance": 0.7,
                  "invent_chance": 0.4, "joke_chance": 0.15, "pay_bias": 0.5}

SAMPLES = [  # net na chale to: (khabar, topic)
    ("Scientists find new way to store solar energy", "Sci-Tech"),
    ("Local team wins the championship in overtime", "Sports"),
    ("New open-source language model released for everyone", "Sci-Tech"),
    ("Farmers adopt low-cost sensors to save water", "World"),
]
AG_NEWS_LABELS = ["World", "Sports", "Business", "Sci-Tech"]
SUBTOPICS = {
    "ai": ["ai", "model", "language", "robot", "software", "algorithm", "data"],
    "energy": ["solar", "energy", "oil", "power", "fuel", "battery"],
    "kheti-paani": ["farm", "farmers", "water", "crop", "rain", "sensors"],
    "khel": ["team", "win", "wins", "match", "game", "champion", "championship"],
    "paisa": ["market", "stock", "bank", "price", "company", "profit", "shares"],
    "rajneeti": ["president", "election", "government", "minister", "war", "police"],
}


def clamp_params(p):
    out = {}
    for k, default in DEFAULT_PARAMS.items():
        lo, hi = BOUNDS[k]
        try:
            v = float(p.get(k, default))
        except (TypeError, ValueError):
            v = default
        v = min(hi, max(lo, v))
        out[k] = int(round(v)) if k in INT_PARAMS else v
    return out


def load_params():
    try:
        with open(STRATEGY_FILE, encoding="utf-8") as f:
            return clamp_params(json.load(f))
    except Exception:
        return clamp_params({})


# ---------------- LLM (optional) ----------------
_llm = None


def think(prompt, fallback):
    """LLM on ho to usse poocho, warna seedha fallback jawab."""
    global _llm
    if not USE_LLM:
        return fallback
    try:
        if _llm is None:
            from transformers import pipeline
            _llm = pipeline("text-generation", model=LLM_MODEL)
        out = _llm(prompt, max_new_tokens=40, do_sample=False)[0]["generated_text"]
        text = out[len(prompt):].strip().split("\n")[0]
        return text[:120] or fallback
    except Exception as e:
        print("LLM nahi chala, niyam use kar raha hoon:", e)
        return fallback


# ---------------- safar aur gyaan ----------------
def fetch_row(offset):
    """HF dataset ki ek row. Wapas: (text, topic, source). Fail hone par (None, None, 'sample')."""
    q = urllib.parse.urlencode({"dataset": DATASET, "config": "default",
                                "split": "train", "offset": offset, "length": 1})
    try:
        with urllib.request.urlopen("https://datasets-server.huggingface.co/rows?" + q, timeout=10) as r:
            row = json.load(r)["rows"][0]["row"]
        text = str(row.get("text") or next(iter(row.values())))[:160]
        label = row.get("label")
        topic = AG_NEWS_LABELS[label] if "ag_news" in DATASET and isinstance(label, int) else "general"
        return text, topic, "dataset"
    except Exception:
        return None, None, "sample"


def subtopic_of(text):
    words = set(re.findall(r"[a-z]+", text.lower()))
    for sub, keys in SUBTOPICS.items():
        if words & set(keys):
            return sub
    return "misc"


def save_knowledge(text, topic, sub, tick, source):
    folder = os.path.join(KNOWLEDGE_DIR, topic, sub, datetime.date.today().strftime("%Y-%m"))
    os.makedirs(folder, exist_ok=True)
    uid = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    path = os.path.join(folder, f"{tick:05d}_{uid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"text": text, "topic": topic, "subtopic": sub, "tick": tick,
                   "source": source, "dataset": DATASET}, f, ensure_ascii=False, indent=2)
    return path


# ---------------- duniya aur agent ----------------
@dataclass
class Home:
    name: str
    food: int
    comfort: int
    rent: int


def new_world():
    return [Home(*h) for h in HOMES]


PERSIST = ["name", "home", "coins", "energy", "hunger", "tick", "learned", "hardship",
           "done_count", "tasks", "done", "knowledge"]


@dataclass
class Agent:
    name: str = "Nexus"
    home: str = "jhopdi"
    coins: int = 20
    energy: int = 100
    hunger: int = 0
    tick: int = 0
    learned: int = 0          # kitni cheezein seekhi
    hardship: int = 0         # kitne step bhookha/thaka raha
    done_count: int = 0
    tasks: list = field(default_factory=list)
    done: list = field(default_factory=list)
    knowledge: list = field(default_factory=list)
    new_tasks_made: int = 0
    params: dict = field(default_factory=load_params)
    sim: bool = False         # True = sirf prayog: na net, na file, na print
    lines: list = field(default_factory=list)

    # --- madadgaar ---
    def wealth(self):
        return "garib" if self.coins < 30 else ("madhyam" if self.coins < 100 else "amir")

    def _clamp(self):
        self.energy = max(0, min(100, self.energy))
        self.hunger = max(0, min(100, self.hunger))

    def log(self, text):
        self._clamp()
        if self.sim:
            return
        line = f"[{self.tick:03d}] ({self.wealth()}, {self.coins} sikke) {text}  | energy={self.energy} hunger={self.hunger}"
        self.lines.append(line)
        print(line)

    def home_obj(self, world):
        return next(h for h in world if h.name == self.home)

    # --- dimaag ---
    def decide(self, world):
        P = self.params
        if self.energy <= P["sleep_below"]:
            return "sleep"
        if self.hunger >= P["eat_above"]:
            if self.home_obj(world).food > 0:
                return "eat"
            if self.coins >= FOOD_PRICE:
                return "buy_food"
            return "work" if self.tasks else "find_new_home"
        if self.tasks:
            return "work"
        w = self.wealth()
        if w == "garib" or (w == "madhyam" and random.Random(self.tick).random() < P["madhyam_job_chance"]):
            return "take_job"
        limit = min(MAX_NEW_TASKS, MAX_NEW_TASKS_LIMIT)
        if self.knowledge and self.new_tasks_made < limit and random.Random(self.tick + 99).random() < P["invent_chance"]:
            return "invent_task"
        return "joke" if random.Random(self.tick + 7).random() < P["joke_chance"] else "explore"

    # --- kaam (haath) ---
    def sleep(self, world):
        gain = 25 + self.home_obj(world).comfort * 3
        self.energy += gain
        self.hunger += 5
        self.log(f"so gaya, energy +{gain}")

    def eat(self, world):
        self.home_obj(world).food -= 1
        self.hunger -= 50
        self.log("khana khaya")

    def buy_food(self, world):
        self.coins -= FOOD_PRICE
        self.home_obj(world).food += 2
        self.log(f"{FOOD_PRICE} sikke ka khana kharida")

    def find_new_home(self, world):
        self.energy -= 15
        self.hunger += 5
        options = [h for h in world if h.name != self.home and h.food > 0 and h.rent <= self.coins]
        if not options:
            self.log("koi ghar nahi mila, kaam dhundhta hoon")
            self.take_job(world)
            return
        best = max(options, key=lambda h: h.food + h.comfort)
        self.log(f"ghar badla: {self.home} -> {best.name}")
        self.home = best.name

    def take_job(self, world):
        rng = random.Random(self.tick + 1)
        job = dict(max(BAZAAR, key=lambda j: j["pay"]) if rng.random() < self.params["pay_bias"] else rng.choice(BAZAAR))
        job["left"] = job["steps"]
        self.tasks.append(job)
        self.log(f"kaam-bazaar se kaam liya: {job['name']} (paisa {job['pay']})")

    def work(self, world):
        t = self.tasks[0]
        t["left"] -= 1
        self.energy -= 8
        self.hunger += 6
        if t["left"] <= 0:
            self.tasks.pop(0)
            self.coins += t["pay"]
            self.done_count += 1
            self.done = (self.done + [t["name"]])[-100:]
            self.log(f"KAAM POORA: {t['name']} (+{t['pay']} sikke)")
        else:
            self.log(f"kaam chal raha: {t['name']} (bacha {t['left']})")

    def explore(self, world):
        self.energy -= 5
        self.hunger += 4
        text, topic, source = (None, None, "sample") if self.sim else fetch_row(self.tick * 7)
        if not text:
            text, topic = random.Random(self.tick).choice(SAMPLES)
        sub = subtopic_of(text)
        self.knowledge = (self.knowledge + [text])[-30:]
        self.learned += 1
        if not self.sim:
            save_knowledge(text, topic, sub, self.tick, source)
        self.log(f"safar ({source}): [{topic}/{sub}] {text[:60]}")

    def invent_task(self, world):
        k = random.Random(self.tick).choice(self.knowledge)   # purani yaaddasht se koi bhi
        fallback = f"'{k[:40]}' ke baare mein 2 line likho"
        name = think(f"Ek chhota kaam likho is khabar par: {k}\nKaam:", fallback)
        self.tasks.append({"name": name, "pay": 0, "steps": 2, "left": 2})
        self.new_tasks_made += 1
        self.log(f"KHUD KA NAYA KAAM ({self.new_tasks_made}/{MAX_NEW_TASKS}): {name}")

    def joke(self, world):
        k = (self.knowledge or [SAMPLES[0][0]])[-1]
        fallback = f"Maine '{k[:35]}' padha, ab samajh aaya: paisa kam hai par khabrein bahut hain!"
        text = think(f"Is khabar par ek chhota mazedaar joke likho: {k}\nJoke:", fallback)
        self.energy -= 2
        self.hunger += 2
        self.log(f"joke: {text}")

    # --- raja, kismat, kiraya ---
    def royal_court(self, world):
        for h in world:
            h.food = min(10, h.food + 1)           # har ghar mein thoda khana ugta hai
        w = self.wealth()
        if w == "amir":
            tax = self.coins * TAX_PERCENT // 100
            self.coins -= tax
            self.log(f"RAJA ne kar liya: -{tax} sikke")
        elif w == "garib":
            self.coins += DAAN
            self.log(f"RAJA ka daan: +{DAAN} sikke")
        h = self.home_obj(world)
        if h.rent:
            if self.coins >= h.rent:
                self.coins -= h.rent
                self.log(f"kiraya diya: -{h.rent}")
            else:
                self.log("kiraya nahi de paya, muft ghar mein gaya")
                self.home = "jhopdi"

    def luck(self):
        r = random.Random(self.tick * 31 + 5).random()
        if r < 0.04:
            self.coins += LUCK_GAIN
            self.log(f"KISMAT: khazana mila (+{LUCK_GAIN})")
        elif r > 0.97 and self.coins > LUCK_LOSS:
            self.coins -= LUCK_LOSS
            self.log(f"KISMAT: chori ho gayi (-{LUCK_LOSS})")

    def step(self, world):
        self.tick += 1
        if self.tick % 10 == 0:
            self.royal_court(world)
        self.luck()
        getattr(self, self.decide(world))(world)
        self._clamp()
        if self.energy == 0 or self.hunger == 100:
            self.hardship += 1


# ---------------- yaaddasht ----------------
def load():
    if os.path.exists(MEMORY):
        with open(MEMORY, encoding="utf-8") as f:
            d = json.load(f)
        world = [Home(**h) for h in d.get("world", [])] or new_world()
        return Agent(**{k: d[k] for k in PERSIST if k in d}), world
    return Agent(), new_world()


def save(agent, world):
    d = {k: getattr(agent, k) for k in PERSIST}
    d["world"] = [h.__dict__ for h in world]
    with open(MEMORY, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    new_file = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        if new_file:
            f.write(f"# {agent.name} ki diary\n")
        f.write(f"\n## Run ke baad tick {agent.tick}\n")
        f.write("\n".join(f"- {l}" for l in agent.lines) + "\n")


def upload_to_hf():
    """Optional: yaaddasht aur gyaan HF dataset par (HF_TOKEN + HF_DATASET_OUT chahiye)."""
    token, repo = os.getenv("HF_TOKEN"), os.getenv("HF_DATASET_OUT")
    if not (token and repo):
        return
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        for fname in (MEMORY, JOURNAL, STRATEGY_FILE, "improvements.md"):
            if os.path.exists(fname):
                api.upload_file(path_or_fileobj=fname, path_in_repo=fname,
                                repo_id=repo, repo_type="dataset")
        if os.path.isdir(KNOWLEDGE_DIR):
            api.upload_folder(folder_path=KNOWLEDGE_DIR, path_in_repo=KNOWLEDGE_DIR,
                              repo_id=repo, repo_type="dataset")
        print("HF dataset par bhej diya:", repo)
    except Exception as e:
        print("HF upload nahi hua:", e)


if __name__ == "__main__":
    agent, world = load()
    for _ in range(STEPS):
        agent.step(world)
    save(agent, world)
    upload_to_hf()
    print(f"\nKaam poore: {agent.done_count} | seekha: {agent.learned} | sikke: {agent.coins} ({agent.wealth()}) | ghar: {agent.home}")
