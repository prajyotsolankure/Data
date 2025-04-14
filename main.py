from flask import Flask, request, jsonify
import os
import openai
from uploaded_file import save_uploaded_file, get_uploaded_df

app = Flask(__name__)
openai.api_key = os.getenv("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")  # or hardcode for testing

# Upload endpoint
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

# Prompt endpoint
@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    prompt = data.get("prompt")

    df = get_uploaded_df()
    if df is None:
        return jsonify({"error": "No file uploaded yet"}), 400

    # Prompt Groq with instruction
    groq_prompt = f"""
You are a data expert. Write Python Pandas code to answer the question:
Question: {prompt}

Assume the dataframe is named `df`. Do not redefine df.
Return only the code, no explanation.
"""

    try:
        response = openai.ChatCompletion.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "user", "content": groq_prompt}
            ]
        )

        code = response['choices'][0]['message']['content']

        # Execute the code safely
        local_vars = {"df": df}
        exec(code, {}, local_vars)
        result = local_vars.get("result", "✅ Code executed. No output returned.")

        return jsonify({"output": str(result), "code": code})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
