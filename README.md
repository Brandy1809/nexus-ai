# Nexus

Ek self-directed AI agent: ghar (GitHub), dimaag (neend, bhook, kaam, jigyasa), paisa aur samaj (garib/madhyam/amir, raja ka tax-daan), safar (Hugging Face dataset), yaaddasht aur khud ko sudharna.

**Setup ke liye `GUIDE.md` padho.**

## Files
| File | Kaam | Agent badal sakta hai? |
|---|---|---|
| `agent.py` | agent ka dimaag aur kaam | prastaav haan (PR + tests + score) |
| `strategy.json` | dimaag ke numbers | haan (`improve.py tune`) |
| `space/app.py` | Space ka Gradio dashboard | prastaav haan (PR) |
| `guardrails.py` | seemayein, score, duniya ke niyam | **nahi** |
| `tests.py` | sudhaar ka darwaza | **nahi** |
| `improve.py` | tune aur code-prastaav | **nahi** |
| `.github/workflows/` | agent-ka-din, agent-sudhaar, space-sync, tests | **nahi** |

## Chalana
```
python tests.py          # jaanch
python agent.py          # agent ka ek din (STEPS=100 python agent.py)
python improve.py tune   # dimaag ke numbers behtar karo
python improve.py code   # AI se code-prastaav (HF_TOKEN chahiye)
```

## Dhyan rakhne ki baat
Agent wahi behtar karta hai jo `guardrails.py` ke score (W_DONE, W_LEARN, W_HARD) mein ginta hai. Score ka formula insaan tay karta hai; badloge to agent ka swabhav badlega.
