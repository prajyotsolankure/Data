import os
import pandas as pd

UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
uploaded_filepath = None

def save_uploaded_file(file, filename):
    global uploaded_filepath
    uploaded_filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(uploaded_filepath)

def get_uploaded_df():
    if uploaded_filepath and os.path.exists(uploaded_filepath):
        if uploaded_filepath.endswith('.csv'):
            return pd.read_csv(uploaded_filepath)
        elif uploaded_filepath.endswith('.xlsx'):
            return pd.read_excel(uploaded_filepath)
        elif uploaded_filepath.endswith('.json'):
            return pd.read_json(uploaded_filepath)
    return None
