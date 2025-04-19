from flask import Flask, request, jsonify, send_file
import pandas as pd
import matplotlib.pyplot as plt
import traceback
import uuid
import io
import os
import requests
import re

app = Flask(_name_)
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
        return jsonify({'message': 'File uploaded successfully', 'columns': df_lower.columns.tolist()}), 200
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

    row_match = re.search(r'(first|last)?\s*(\d+)\s+rows?', prompt)
    view_keywords = ['show', 'display', 'table', 'print', 'head', 'tail', 'first', 'last', 'top', 'bottom']

    if any(word in prompt for word in view_keywords) or row_match:
        try:
            num_rows = 5
            is_tail = False

            if row_match:
                num_rows = int(row_match.group(2))
                if row_match.group(1) and row_match.group(1) in ['last', 'tail', 'bottom']:
                    is_tail = True

            preview_df = df_lower.tail(num_rows) if is_tail else df_lower.head(num_rows)

            rows, cols = preview_df.shape
            fig_width = max(4, cols * 2)
            fig_height = max(1.5, rows * 0.7)

            fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=300)
            ax.axis('off')

            table = ax.table(cellText=preview_df.values,
                             colLabels=preview_df.columns,
                             cellLoc='center',
                             loc='center')

            table.auto_set_font_size(False)
            font_size = max(8, min(14, int(280 / max(cols, 1))))
            table.set_fontsize(font_size)
            table.scale(1.1, 1.4)

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

    try:
        code_prompt = f"""
You are a Python data analyst. Write only valid Python Pandas code to answer the question below using the DataFrame df_lower.

DataFrame Notes:
- All column names are in lowercase.
- If the question can't be answered using pandas (e.g., it's unrelated to tabular data or about external knowledge), return: "not_possible".

Question: {prompt}

Rules:
- Assign the final answer to a variable named result.
- No explanations, markdown, or print statements.
- Only return code or the word "not_possible".
"""
        code = call_groq(code_prompt)
        code = code.strip().strip("python").strip("`").strip()

        if code.lower() == "not_possible":
            return jsonify({"output": "This question cannot be answered using pandas."})

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
Raw result:

{result_str}

Now summarize this result briefly and clearly without excessive explanation. Just return the core answer.
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

# ✅ Corrected main entry point
if _name_ == '_main_':
    app.run(host='0.0.0.0', port=5000)s
