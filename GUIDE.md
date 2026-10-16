# Nexus: shuru se aakhir tak guide

Is guide ke baad aapke paas hoga: GitHub par agent ka **ghar**, Hugging Face par uski **yaaddasht aur gyaan** (folder-wise), ek **Space** jo uska kaam dikhata hai, aur roz apne aap chalne wali **GitHub Actions**.

## 0. Naam (yahi rakhna, taaki sab files aapas mein judi rahein)

| Cheez | Naam | Kahan |
|---|---|---|
| GitHub repo (asli ghar, code) | `nexus-ai` | github.com/`<aapka-github-username>`/nexus-ai |
| HF dataset (yaaddasht + gyaan) | `Brandyo/nexus-memory` | huggingface.co/datasets/Brandyo/nexus-memory |
| HF Space (dashboard) | `Brandyo/nexus-ghar` | huggingface.co/spaces/Brandyo/nexus-ghar |

(`Brandyo` aapka HF username hai. Safar ka dataset alag hai: default `fancyzhx/ag_news`, jo pehle se bana hua hai.)

## 1. HF dataset banao (khaali)
1. huggingface.co/new-dataset kholo.
2. Owner: `Brandyo`, Dataset name: `nexus-memory`, **Public** chuno (private rakhoge to Space mein token daalna padega).
3. Create dataset. Kuch aur nahi karna. Agent khud isme ye folder banayega:

```
knowledge/
  Sci-Tech/
    ai/
      2026-10/
        00045_842af4c0.json      <- ek seekhi hui cheez
    energy/2026-10/...
  Sports/khel/2026-10/...
memory.json        <- agent ki yaaddasht
journal.md         <- diary
strategy.json      <- uske dimaag ke numbers
improvements.md    <- sudhaar ka khaata
```
Folder ka tareeka: `knowledge / topic / subtopic / saal-mahina / file`. Topic dataset ke label se aata hai (World, Sports, Business, Sci-Tech), subtopic khabar ke shabdon se (ai, energy, khel, paisa...).

## 2. HF Space banao (aapki screen wala page)
1. Owner: `Brandyo`, Space name: `nexus-ghar`.
2. Short description: `Nexus ke ghar ka dashboard`. License: `mit`.
3. SDK: **Gradio**, template: **Blank**.
4. Hardware: **ZeroGPU** chuno. Ye aapka pehla Space hai, isliye HF ek Space ke liye free deta hai (baaki paid). Dashboard ko GPU ki zarurat nahi, ZeroGPU bas jagah ki tarah kaam aayega; `app.py` mein ek dummy GPU function pehle se hai taaki "no GPU function detected" error na aaye. Agar kabhi CPU Basic free mile to wo bhi chalega.
5. Create Space. Ab ise haath se kuch mat badalna; GitHub se files apne aap aayengi.

## 3. GitHub repo banao aur files daalo
1. github.com/new: naam `nexus-ai`. **Public** rakho (public repo par Actions free hai).
2. Zip ki saari files repo mein daalo, folder structure waisa hi (khaaskar `.github/workflows/` aur `space/`). Kuch file managers `.github` folder chhupa dete hain, use mat chhodna.

   Command se karna ho to (folder ke andar):
   ```
   git init
   git add .
   git commit -m "pehla din"
   git branch -M main
   git remote add origin https://github.com/<aapka-github-username>/nexus-ai.git
   git push -u origin main
   ```
3. Repo -> Settings -> Actions -> General -> **Workflow permissions**: "Read and write permissions" chuno, aur "Allow GitHub Actions to create and approve pull requests" tick karo. Save.

## 4. Token, secrets aur variables
1. huggingface.co/settings/tokens -> New token -> type **Write** -> copy karo. **Ye token kisi chat mein mat bhejna** (mujhe bhi nahi).
2. GitHub repo -> Settings -> Secrets and variables -> Actions:
   - **Secrets** tab -> New repository secret: `HF_TOKEN` = (token)
   - **Variables** tab, ye banao:

| Variable | Value | Zaruri? |
|---|---|---|
| `HF_DATASET_OUT` | `Brandyo/nexus-memory` | haan |
| `HF_SPACE` | `Brandyo/nexus-ghar` | haan |
| `HF_DATASET` | safar ka dataset (default `fancyzhx/ag_news`) | nahi |
| `USE_LLM` | `1` -> chhota open-source LLM (Qwen 0.5B) sochne mein madad kare | nahi |
| `CODE_IMPROVE` | `1` -> AI se code-sudhaar ke PR | nahi, baad mein |
| `CODE_MODEL` | koi code model, default `Qwen/Qwen2.5-Coder-32B-Instruct` | nahi |

## 5. Pehli baar chalao
1. Repo -> Actions -> **space-sync** -> Run workflow (Space par dashboard pahunch jayega).
2. Actions -> **agent-ka-din** -> Run workflow. Ye pehle `tests.py` chalata hai, phir agent ka ek din.
3. Check karo: HF dataset mein `knowledge/...` folders aaye? Space kholo, "Refresh" dabao: Halat, Diary, Gyaan, Sudhaar tabs dikhne chahiye.
4. Iske baad roz subah 9:00 IST par agent apne aap chalega.

## 6. Agent khud ko kaise sudharta hai (teen star)

| Star | Kya badalta hai | Kaun roakta hai | Kab |
|---|---|---|---|
| 1. Gyaan | naya `knowledge/` data | har run | roz |
| 2. Tune (`improve.py tune`) | sirf `strategy.json` ke 6 numbers (neend, bhook, kaam ki pasand...) | numbers `guardrails.py` ki seema mein, train + holdout dono par score badhna chahiye | har ravivaar, seedha commit |
| 3. Code (`improve.py code`) | `agent.py` aur `space/app.py` ka naya version, AI model likhta hai | static jaanch, `tests.py`, score jaanch, phir **Pull Request** | har ravivaar, agar `CODE_IMPROVE=1` |

Agent **kabhi** nahi badal sakta: `guardrails.py` (seema, score, duniya ke niyam), `improve.py`, `tests.py`, `.github/` (workflows), secrets. PR ko aap dekhkar merge karte ho; `improvements.md` mein likha hota hai kya badla aur score kitna badha.

## 7. GitHub aur Space ke beech sync
Do-tarfa automatic sync (GitHub <-> Space) mat banao: dono jagah ek saath badlaav hua to takraav (conflict) aur loop banta hai. Hum **GitHub ko asli ghar** maante hain: Space ki `app.py` bhi GitHub ke `space/` folder mein rehti hai. Agent `space/app.py` sudhaarta hai -> PR -> merge -> `space-sync` use Space par bhej deta hai. Natija wahi: agent dono ko behtar kar sakta hai, bas ek hi raaste se.

## 8. Dikkat aaye to
- **402 / 403 error HF par:** token Write wala nahi hai, ya dataset/Space ka naam `HF_DATASET_OUT` / `HF_SPACE` mein galat hai.
- **Actions mein "push rejected":** Settings -> Actions -> Workflow permissions "Read and write" karo.
- **PR nahi ban raha:** "Allow GitHub Actions to create and approve pull requests" tick karo.
- **Space "Runtime error":** Logs tab dekho; aksar dataset ka naam galat hota hai. `HF_DATASET_OUT` ko Space ke Settings -> Variables mein bhi daal sakte ho.
- **Dataset private rakha:** Space -> Settings -> Secrets mein `HF_TOKEN` daalo.

## 9. Sir ko ek line mein
"Agent ke paas ghar, dimaag (neend-bhook-kaam-jigyasa), paisa aur samaj (garib-amir-raja) hai; wo HF datasets se seekhta hai, gyaan topic-wise folders mein rakhta hai, aur apne dimaag ke numbers tests aur seemaon ke andar khud behtar karta hai."
