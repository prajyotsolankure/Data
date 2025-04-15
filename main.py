from flask import Flask, request, jsonify
import os
import pandas as pd
import requests
from uploaded_file import save_uploaded_file, get_uploaded_df

app = Flask(__name__)

# Replace with your actual Groq API key
GROQ_API_KEY = "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"

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

    # Generate the code using Groq API
    groq_prompt = f"""
    You are a data analyst. Write Python Pandas code to answer this question:
    Question: {prompt}
    Use the dataframe `df`. Return only the code, nothing else.
    """

    try:
        groq_response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mixtral-8x7b-32768",
                "messages": [{"role": "user", "content": groq_prompt}],
                "temperature": 0.2
            }
        )

        groq_data = groq_response.json()
        code = groq_data['choices'][0]['message']['content']

        local_vars = {"df": df}
        exec(code, {}, local_vars)
        result = local_vars.get("result", "✅ Code executed. No output returned.")

        return jsonify({"output": str(result), "code": code})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
