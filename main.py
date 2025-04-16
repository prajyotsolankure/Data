from flask import Flask, request, jsonify
import pandas as pd
import traceback
import requests
import os

app = Flask(__name__)

# Groq API credentials
GROQ_API_KEY = "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"
MODEL = "llama3-70b-8192"  # Updated model since mixtral was deprecated

# Global variable for DataFrame
df_lower = None

# Upload route
@app.route('/upload', methods=['POST'])
def upload():
    global df_lower
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        elif file.filename.endswith('.json'):
            df = pd.read_json(file)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400

        # Save the dataframe with lowercase column names
        df_lower = df.copy()
        df_lower.columns = df_lower.columns.str.lower()

        return jsonify({'message': 'File uploaded and processed successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Ask route
@app.route('/ask', methods=['POST'])
def ask():
    global df_lower
    if df_lower is None:
        return jsonify({"error": "Please upload a dataset first."}), 400

    data = request.json
    prompt = data.get("prompt")

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    # 1. Use Groq to generate Pandas code
    try:
        code_prompt = f"""
You are a helpful data analyst. Write ONLY valid Python Pandas code that answers the following question using the DataFrame `df_lower`:

Note: `df_lower` has all lowercase column names.

Question: {prompt}

Only return Python code that assigns the answer to a variable named `result`. Do NOT include markdown, explanations, or text.
"""
        code = call_groq(code_prompt)
        if not code:
            return jsonify({"error": "Failed to generate code from Groq API."}), 500
        code = code.strip().strip("```python").strip("```")

        # 2. Execute the code
        local_vars = {'df_lower': df_lower}
        exec(code, {}, local_vars)
        result = local_vars['result']

        # 3. Convert result to string (head for large DataFrames)
        if isinstance(result, pd.DataFrame):
            result_str = result.head(5).to_string(index=False)
        else:
            result_str = str(result)

    except Exception as e:
        return jsonify({"error": f"Failed to run code: {str(e)}", "trace": traceback.format_exc()}), 500

    # 4. Send result back to Groq for concise formatting
    try:
        reformat_prompt = f"""
The user asked: "{prompt}"

This is the raw result from executing Python Pandas code:

{result_str}

Now summarize this result concisely without excessive details. Just provide the answer.
"""
        concise_answer = call_groq(reformat_prompt)
        if not concise_answer:
            return jsonify({"error": "Failed to reformat result using Groq API."}), 500

        return jsonify({"output": concise_answer})

    except Exception as e:
        return jsonify({"error": f"Failed to contact Groq API for reformatting: {str(e)}"}), 500


# Call Groq helper
def call_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    })

    try:
        result = response.json()
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        print("Raw response:", response.text)
        return None

    if 'choices' in result and result['choices']:
        return result['choices'][0]['message']['content']
    else:
        print("❌ Groq did not return valid choices:", result)
        return None


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
