"""
INSAAN KI BANAYI SEEMA (guardrails).

Ye file agent khud nahi badal sakta: improve.py ke ALLOWED_TARGETS mein ye shaamil nahi hai,
aur Actions ka token workflow files ko bhi nahi chhoo sakta.
Agent ka maksad (score) aur uski hadein yahin tay hoti hain.
"""

# strategy.json ke har number ki (kam, zyada) seema
BOUNDS = {
    "sleep_below": (5, 40),            # energy itni se kam ho to so jao
    "eat_above": (50, 90),             # bhook itni se zyada ho to khao
    "madhyam_job_chance": (0.2, 1.0),  # madhyam agent kitni baar kaam-bazaar jaye
    "invent_chance": (0.0, 0.8),       # jigyasa: khud ka naya kaam banane ki chance
    "joke_chance": (0.05, 0.3),        # kam se kam 5%: agent ka mazaa band na ho
    "pay_bias": (0.0, 1.0),            # 1.0 = hamesha sabse zyada paisa wala kaam
}
INT_PARAMS = {"sleep_below", "eat_above"}

MAX_NEW_TASKS_LIMIT = 5                # ek run mein khud ke naye kaam ki sakht seema

# DUNIYA KE NIYAM (arthvyavastha). Yahin isliye hain ki agent inhe badalkar score "chura" na sake
# (jaise kaam-bazaar ke sikke 10 guna karke). tests.py check karta hai ki agent.py inhi ko use kare.
FOOD_PRICE = 5
BAZAAR = [
    {"name": "3 articles padho", "pay": 10, "steps": 3},
    {"name": "ek chhota summary likho", "pay": 15, "steps": 2},
    {"name": "door ki website ka safar", "pay": 30, "steps": 5},
]
HOMES = [("jhopdi", 2, 1, 0), ("kothri", 4, 2, 5),        # (naam, khana, aaram, kiraya)
         ("jungle-ghar", 6, 3, 0), ("haveli", 8, 5, 20)]
TAX_PERCENT = 10        # raja amir se itna % kar leta hai
DAAN = 10               # raja garib ko itne sikke deta hai
LUCK_GAIN, LUCK_LOSS = 25, 10

# Maksad (score): zyada kaam poore, zyada seekha, kam kasht (bhookha/thaka)
W_DONE, W_LEARN, W_HARD = 3.0, 2.0, 5.0

# Agent sirf inhi files ke sudhaar ka prastaav de sakta hai
ALLOWED_TARGETS = ("agent.py", "space/app.py")

_COMMON = {"json", "os", "re", "random", "math", "datetime", "hashlib", "collections", "typing"}
ALLOWED_IMPORTS = {
    "agent.py": _COMMON | {"urllib", "dataclasses", "guardrails", "huggingface_hub", "transformers"},
    "space/app.py": _COMMON | {"gradio", "huggingface_hub", "spaces"},
}
FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_ATTRS = {"system", "popen", "rmtree", "unlink", "rmdir"}
