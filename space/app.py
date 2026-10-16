"""Nexus ka ghar: HF dataset se agent ki halat, diary, gyaan ka folder-tree aur sudhaar dikhata hai."""
import json
import os

import gradio as gr
from huggingface_hub import HfApi, hf_hub_download

try:   # ZeroGPU hardware par hi 'spaces' maujood hota hai; baaki jagah ye hissa chhoot jata hai
    import spaces

    @spaces.GPU
    def _gpu_dummy():
        """Kabhi call nahi hota (GPU quota nahi lagta). ZeroGPU ko bas ek GPU function dikhna chahiye."""
        return "ok"
except ImportError:
    pass

DATASET = os.getenv("HF_DATASET_OUT", "Brandyo/nexus-memory")
TOKEN = os.getenv("HF_TOKEN")   # dataset private ho to Space ke Secrets mein daalo


def _read(name):
    try:
        path = hf_hub_download(DATASET, name, repo_type="dataset", token=TOKEN, force_download=True)
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def halat():
    raw = _read("memory.json")
    if not raw:
        return "Abhi koi yaaddasht nahi mili. Agent ki pehli run ke baad yahan dikhega."
    m = json.loads(raw)
    return (f"### {m.get('name', 'agent')}\n"
            f"- ghar: **{m.get('home')}**\n- sikke: **{m.get('coins')}**\n"
            f"- energy: {m.get('energy')} | bhook: {m.get('hunger')}\n"
            f"- kaam poore: {m.get('done_count', len(m.get('done', [])))}\n"
            f"- seekhi hui cheezein: {m.get('learned', 0)}\n- kitne step jiya: {m.get('tick')}")


def diary():
    raw = _read("journal.md")
    return "\n".join(raw.splitlines()[-80:]) if raw else "Diary abhi khaali hai."


def gyaan():
    try:
        files = [f for f in HfApi().list_repo_files(DATASET, repo_type="dataset", token=TOKEN)
                 if f.startswith("knowledge/")]
    except Exception:
        return "Dataset abhi nahi mila ya khaali hai."
    tree = {}
    for f in files:
        node = tree
        for part in f.split("/")[1:-1]:
            node = node.setdefault(part, {})
        node["_n"] = node.get("_n", 0) + 1

    def count(n):
        return n.get("_n", 0) + sum(count(v) for k, v in n.items() if k != "_n")

    def render(n, depth):
        rows = []
        for k in sorted(x for x in n if x != "_n"):
            rows.append("    " * depth + f"{k}/  ({count(n[k])})")
            rows.extend(render(n[k], depth + 1))
        return rows

    return "```\nknowledge/ (%d)\n%s\n```" % (len(files), "\n".join(render(tree, 1))) if files else "Abhi koi gyaan save nahi hua."


def sudhaar():
    log = _read("improvements.md") or "Abhi koi sudhaar nahi hua."
    strat = _read("strategy.json") or "{}"
    return f"{log}\n\n### Abhi ka dimaag (strategy.json)\n```json\n{strat}\n```"


def refresh():
    return halat(), diary(), gyaan(), sudhaar()


with gr.Blocks(title="Nexus ka ghar") as demo:
    gr.Markdown("# 🏡 Nexus ka ghar\nYe agent roz GitHub Actions par jeeta hai. Yahan uski halat, diary, gyaan aur sudhaar dikhte hain.")
    with gr.Tab("Halat"):
        out_halat = gr.Markdown()
    with gr.Tab("Diary"):
        out_diary = gr.Markdown()
    with gr.Tab("Gyaan (folders)"):
        out_gyaan = gr.Markdown()
    with gr.Tab("Sudhaar"):
        out_sudhaar = gr.Markdown()
    gr.Button("Refresh").click(refresh, outputs=[out_halat, out_diary, out_gyaan, out_sudhaar])
    demo.load(refresh, outputs=[out_halat, out_diary, out_gyaan, out_sudhaar])

if __name__ == "__main__":
    demo.launch()
