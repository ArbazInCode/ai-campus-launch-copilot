# AI Campus Launch Copilot

Enter a city and a sport, and get a complete launch kit for a new sports-school campus in about a minute:

- **Positioning** – headline, tagline, and selling points
- **Website copy** + a **ready-to-host landing page** (`index.html`)
- **Facebook & Instagram ads** – 3 versions to A/B test, audience, and a budget split by phase
- **Banners** in 3 sizes (feed, story, link ad), generated in Python with Pillow
- **Event plan** – open houses, tryouts, and info sessions worked backward from the opening date (moved to Saturdays when possible)
- **Hiring plan** – openings calculated from staffing ratios, with ready-to-post job descriptions
- **Launch checklist** – editable, dated, with a timeline chart and Excel export
- **One-click export** – everything in a ZIP

AI writes the words (Google Gemini). Python does the math (dates, staffing, budgets), so numbers are always consistent. Without an API key, or if the free limit is reached, the app falls back to polished built-in templates and never breaks.

> Independent concept by Arbaz Abdul. Not an official Texas Sports Academy product. Sample planning only.

## Tech
Python · Streamlit · Google Gemini API (`google-genai`) · Pillow · pandas · Altair · openpyxl · pytest

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Get a free Gemini API key
1. Go to **aistudio.google.com** and sign in with Google.
2. Click **Get API key → Create API key** and copy it.

## Deploy free on Streamlit Community Cloud
1. Upload this folder to a **public GitHub repository**.
2. Go to **share.streamlit.io**, sign in with GitHub, click **Create app**, pick the repository, and set the main file to `app.py`.
3. Before deploying, open **Advanced settings → Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
4. Click **Deploy**. Your link looks like `https://your-app-name.streamlit.app`.

Never put the API key in the code or upload `secrets.toml` to GitHub.

## Tests
```bash
python -m pytest -q
```
27 tests cover timeline planning (ordering, Saturdays, compressed runways, no past dates), staffing ratios, budgets that always sum exactly, AI response validation and every failure fallback (quota, bad key, wrong model, malformed JSON), banner sizes, Excel/ZIP exports, HTML escaping, and the full Streamlit interface.
