# Gross to Net Pay Calculator | Expats (Streamlit)

This is a Streamlit app for estimating local taxes and a US overlay (FEIE + standard deduction + FTC), with editable progressive tax brackets.

## Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
# or: streamlit run New10.py
```

## Deploy to Streamlit Community Cloud
1. Push this folder to a new GitHub repository (public or private).
2. Go to https://streamlit.io/cloud and click **New app**.
3. Choose your repo, branch (e.g., `main`), and main file path: `streamlit_app.py`.
4. Click **Deploy**. The app builds and gives you a public URL.
5. To update, push new commits to the repo; Streamlit redeploys automatically.

### Tips
- If you rename the file, update the **Main file path** in the Streamlit app settings.
- Check **Logs** in the Streamlit Cloud dashboard if the build fails (usually a `requirements.txt` issue).
- You can add secrets later at **App settings → Secrets** if needed.
