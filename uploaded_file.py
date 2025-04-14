import pandas as pd

# Store uploaded file data here
uploaded_file_data = {
    "filename": None,
    "df": None
}

def save_uploaded_file(file, filename):
    if filename.endswith(".csv"):
        df = pd.read_csv(file)
    elif filename.endswith(".xlsx"):
        df = pd.read_excel(file)
    elif filename.endswith(".json"):
        df = pd.read_json(file)
    else:
        raise ValueError("Unsupported file type")

    uploaded_file_data["filename"] = filename
    uploaded_file_data["df"] = df

def get_uploaded_df():
    return uploaded_file_data["df"]
