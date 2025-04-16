from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Use your provided Groq API key here
GROQ_API_KEY = "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"
MODEL = "mixtral-8x7b-32768"  # You can use the correct model for your use case

# Function to call Groq API
def groq_api_call(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Create Groq prompt to generate Python code for Pandas
    groq_prompt = f"""
    You are a helpful data analyst. Write **only** valid Python Pandas code that answers the following question using the DataFrame `df_lower`:
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

    # Return the code as it is (no reformatting)
    return jsonify({"output": code})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
