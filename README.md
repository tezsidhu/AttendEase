# AttendEase

A local-first student attendance tracker built with Streamlit.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run attendease.py
```

## Deploy

Deploy `attendease.py` from this repository using Streamlit Community Cloud.
Community Cloud requires `requirements.txt` so it can install Streamlit.

## Important prototype limitations

- The current version stores data in `attendease_data.json` next to the app.
- Hosted local files may not be durable across restarts/redeployments.
- This prototype does not have user accounts, authorization, or cloud database storage.
- Do not enter sensitive or real student records until persistent storage and authentication are implemented.
