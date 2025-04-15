from flask import Flask, request, jsonify
import pandas as pd
import requests
from uploaded_file import save_uploaded_file, get_uploaded_df

# Replace this with your actual Groq API key
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    filename = file.filename

    try:
        save_uploaded_file(file, filename)
        return jsonify({"message": f"{filename} uploaded successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    prompt = data.get("prompt")

    df = get_uploaded_df()
    if df is None:
        return jsonify({"error": "No file uploaded yet"}), 400

    groq_prompt = f"""
    You are a data expert. Write Python Pandas code to answer the question:
    Question: {prompt}
    Assume the dataframe is named `df`. Do not redefine df.
    Return only the code, no explanation.
    """

    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "user", "content": groq_prompt}
            ],
            "temperature": 0.2
        }

        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        code = response.json()["choices"][0]["message"]["content"]

        local_vars = {"df": df}
        exec(code, {}, local_vars)
        result = local_vars.get("result", "✅ Code executed. No output returned.")

        return jsonify({"output": str(result), "code": code})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
