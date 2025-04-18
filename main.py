from flask import Flask, request, jsonify, send_file
import pandas as pd
import matplotlib.pyplot as plt
import traceback
import uuid
import io
import os
import requests
import re

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

df_lower = None
GROQ_API_KEY = "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"
MODEL = "llama3-70b-8192"

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

        df_lower = df.copy()
        df_lower.columns = df_lower.columns.str.lower()
        return jsonify({'message': 'File uploaded and processed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask():
    global df_lower
    if df_lower is None:
        return jsonify({"error": "Please upload a dataset first."}), 400

    data = request.json
    prompt = data.get("prompt", "").lower()

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    # Check for prompts like "show 5 rows", "give 10 rows", etc.
    row_match = re.search(r'(\d+)\s+rows?', prompt)
    show_table_keywords = ['show', 'display', 'table', 'print', 'head']
    if any(word in prompt for word in show_table_keywords) or row_match:
        try:
            num_rows = int(row_match.group(1)) if row_match else 5
            preview_df = df_lower.head(num_rows)

            # HD table rendering
            rows, cols = preview_df.shape
            fig_width = max(4, cols * 2.5)
            fig_height = max(1.5, rows * 0.7)

            fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=300)
            ax.axis('off')

            table = ax.table(cellText=preview_df.values,
                             colLabels=preview_df.columns,
                             cellLoc='center',
                             loc='center')

            table.auto_set_font_size(False)
            table.set_fontsize(14)
            table.scale(1.2, 1.5)

            plt.tight_layout(pad=0.2)

            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', bbox_inches='tight')
            img_buf.seek(0)

            image_id = f"{uuid.uuid4()}.png"
            img_path = os.path.join(UPLOAD_FOLDER, image_id)
            with open(img_path, 'wb') as f:
                f.write(img_buf.read())

            return jsonify({"image_url": f"/image/{image_id}"})

        except Exception as e:
            return jsonify({'error': f'Failed to generate image: {str(e)}', "trace": traceback.format_exc()}), 500

    # Otherwise, use Groq to generate code
    try:
        code_prompt = f"""
You are a helpful data analyst. Write ONLY valid Python Pandas code that answers the following question using the DataFrame `df_lower`.
Note: `df_lower` has all lowercase column names.
Question: {prompt}
Only return Python code that assigns the answer to a variable named `result`. Do NOT include markdown or explanations.
"""
        code = call_groq(code_prompt)
        code = code.strip().strip("```python").strip("```")

        local_vars = {'df_lower': df_lower}
        exec(code, {}, local_vars)
        result = local_vars['result']

        if isinstance(result, pd.DataFrame):
            result_str = result.head(5).to_string(index=False)
        else:
            result_str = str(result)

    except Exception as e:
        return jsonify({"error": f"Failed to run code: {str(e)}", "trace": traceback.format_exc()}), 500

    try:
        reformat_prompt = f"""
The user asked: "{prompt}"
This is the raw result from executing Python Pandas code:

{result_str}

Now summarize this result concisely without excessive details. Just provide the answer.
"""
        concise_answer = call_groq(reformat_prompt)
        return jsonify({"output": concise_answer})

    except Exception as e:
        return jsonify({"error": f"Failed to contact Groq API for reformatting: {str(e)}"}), 500

@app.route('/image/<image_id>')
def get_image(image_id):
    try:
        return send_file(os.path.join(UPLOAD_FOLDER, image_id), mimetype='image/png')
    except:
        return jsonify({'error': 'Image not found'}), 404

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
        return result['choices'][0]['message']['content'] if 'choices' in result else None
    except:
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
