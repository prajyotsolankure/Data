from flask import Flask, request, jsonify
import os
import pandas as pd
import requests
from uploaded_file import save_uploaded_file, get_uploaded_df

app = Flask(__name__)

# Replace with your Groq API key
GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama3-70b-8192"  # Updated model since mixtral was deprecated

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

    # Create lowercase column version of df
    df_lower = df.copy()
    df_lower.columns = [col.lower() for col in df.columns]

    # Prompt for Groq API
    groq_prompt = f"""
You are a helpful data analyst. Write **only** valid Python Pandas code that answers the following question using the DataFrame `df_lower`.
Note: `df_lower` has all lowercase column names, even if the original columns were uppercase.

Question: {prompt}

Only return code that assigns the answer to a variable named `result`.
Do not return markdown or explanations.
"""

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": groq_prompt}],
                "temperature": 0.2
            }
        )

        data = response.json()

        if 'choices' not in data or not data['choices']:
            return jsonify({"error": "Failed to generate valid code from Groq API."}), 500

        code = data['choices'][0]['message']['content'].strip()

        # Clean markdown backticks if any
        if code.startswith("```"):
            code = code.strip("```").strip("python").strip()

        local_vars = {"df": df, "df_lower": df_lower}

        try:
            exec(code, {}, local_vars)
            result = local_vars.get("result", "✅ Code executed but no result returned.")
            return jsonify({"output": str(result), "code": code})
        except Exception as e:
            return jsonify({"code": code, "error": f"Groq returned invalid Python code: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Failed to contact Groq API: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

