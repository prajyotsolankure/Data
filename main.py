from flask import Flask, request, jsonify
import os
import openai
import pandas as pd
from uploaded_file import save_uploaded_file, get_uploaded_df

# Initialize Flask app
app = Flask(__name__)

# Directly set OpenAI API key (hardcoded)
openai.api_key = "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"  # Replace with your actual OpenAI API key

# Upload endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    filename = file.filename

    try:
        # Save the uploaded file
        save_uploaded_file(file, filename)
        return jsonify({"message": f"{filename} uploaded successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Prompt endpoint
@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    prompt = data.get("prompt")

    # Get the uploaded dataframe
    df = get_uploaded_df()
    if df is None:
        return jsonify({"error": "No file uploaded yet"}), 400

    # Groq-style prompt for Pandas code generation
    groq_prompt = f"""
    You are a data expert. Write Python Pandas code to answer the question:
    Question: {prompt}
    Assume the dataframe is named `df`. Do not redefine df.
    Return only the code, no explanation.
    """

    try:
        # Call OpenAI API to get the Python code
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use the appropriate model for your case
            messages=[{"role": "user", "content": groq_prompt}]
        )

        # Extract the code from the OpenAI response
        code = response['choices'][0]['message']['content']

        # Execute the code in a controlled environment (local variables)
        local_vars = {"df": df}
        exec(code, {}, local_vars)

        # Retrieve the result from the executed code
        result = local_vars.get("result", "✅ Code executed. No output returned.")

        return jsonify({"output": str(result), "code": code})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
