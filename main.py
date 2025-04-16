from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

GROQ_API_KEY = "your-groq-api-key"  # Replace with your actual key
MODEL = "mixtral-8x7b-32768"  # Replace with your model name

# Function to call Groq API
def groq_api_call(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Create Groq prompt to generate Python code for Pandas
    groq_prompt = f"""
    You are a helpful data analyst. Write **only** valid Python Pandas code that answers the following question using the DataFrame `df_lower`.
    Note: `df_lower` has all lowercase column names, even if the original columns were uppercase.

    Question: {prompt}

    Only return code that assigns the answer to a variable named `result`.
    Do not return markdown or explanations.
    """
    
    response = requests.post(
        url,
        headers=headers,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": groq_prompt}],
            "temperature": 0.2
        }
    )

    return response.json()

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    prompt = data.get("prompt")

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    # Step 1: Call Groq API to process the user prompt
    try:
        groq_response = groq_api_call(prompt)
        if 'choices' not in groq_response or not groq_response['choices']:
            return jsonify({"error": "Failed to generate valid code from Groq API."}), 500

        code = groq_response['choices'][0]['message']['content'].strip()

        # Clean markdown backticks if any
        if code.startswith("```"):
            code = code.strip("```").strip("python").strip()

    except Exception as e:
        return jsonify({"error": f"Failed to contact Groq API: {str(e)}"}), 500

    # Step 2: Reformat output (using Groq API again for better response formatting)
    try:
        reformat_prompt = f"""
        Reformat the following response from Python code to a clean, user-friendly format:
        {code}
        Please return the result in a readable, neat format with clear explanations if possible.
        """

        groq_reformat_response = groq_api_call(reformat_prompt)
        if 'choices' not in groq_reformat_response or not groq_reformat_response['choices']:
            return jsonify({"error": "Failed to reformat output using Groq API."}), 500

        final_response = groq_reformat_response['choices'][0]['message']['content'].strip()
        
    except Exception as e:
        return jsonify({"error": f"Failed to contact Groq API for reformatting: {str(e)}"}), 500

    return jsonify({"output": final_response})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
