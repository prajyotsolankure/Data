from flask import Flask, request, jsonify, send_file
import pandas as pd
import os
import uuid
import matplotlib.pyplot as plt
from groq import Groq
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

client = Groq(api_key="YOUR_GROQ_API_KEY")  # Replace with your actual key

df_lower = None  # Global DataFrame


@app.route('/upload', methods=['POST'])
def upload_file():
    global df_lower
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_ext = file.filename.rsplit('.', 1)[1].lower()
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        if file_ext == 'csv':
            df_lower = pd.read_csv(filepath)
        elif file_ext in ['xls', 'xlsx']:
            df_lower = pd.read_excel(filepath)
        elif file_ext == 'json':
            df_lower = pd.read_json(filepath)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        df_lower.columns = df_lower.columns.str.lower()
        return jsonify({'message': 'File uploaded and processed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask():
    global df_lower
    data = request.get_json()
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({'error': 'Prompt missing'}), 400

    if df_lower is None:
        return jsonify({'error': 'No file uploaded yet'}), 400

    # Check if prompt requires data display
    if any(word in prompt.lower() for word in ['show', 'display', 'print', 'give rows', 'head(', 'records']):
        try:
            # Limit rows to display
            if 'first 5' in prompt.lower() or '5 rows' in prompt.lower():
                output_df = df_lower.head(5)
            elif '10 rows' in prompt.lower():
                output_df = df_lower.head(10)
            else:
                output_df = df_lower.head(8)

            # Plot as image
            fig, ax = plt.subplots(figsize=(10, 2 + 0.3 * len(output_df)))
            ax.axis('off')
            tbl = ax.table(cellText=output_df.values,
                           colLabels=output_df.columns,
                           cellLoc='center', loc='center')
            tbl.scale(1, 1.5)
            plt.tight_layout()

            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png')
            img_buf.seek(0)
            image_id = str(uuid.uuid4()) + ".png"
            image_path = os.path.join("uploads", image_id)
            with open(image_path, "wb") as f:
                f.write(img_buf.read())

            return jsonify({'image_url': f'/image/{image_id}'})

        except Exception as e:
            return jsonify({'error': f'Failed to generate image: {str(e)}'}), 500

    # Otherwise use LLM
    try:
        messages = [{"role": "user", "content": f"The user uploaded this data with columns {list(df_lower.columns)}. Based on that, answer this query: {prompt}"}]

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama3-70b-8192"
        )

        response_text = chat_completion.choices[0].message.content
        return jsonify({'output': response_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/image/<image_id>')
def get_image(image_id):
    try:
        return send_file(os.path.join("uploads", image_id), mimetype='image/png')
    except:
        return jsonify({'error': 'Image not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
