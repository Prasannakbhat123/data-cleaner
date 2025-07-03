from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
import numpy as np
import datetime
from werkzeug.utils import secure_filename
from data_cleaning_bot import DataCleaningBot
import json
import pandas as pd

# Custom JSON encoder to handle NaN values and NumPy types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            # Handle NaN, Infinity, -Infinity specially
            if np.isnan(obj):
                return None
            if np.isinf(obj):
                return str(obj)
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        elif isinstance(obj, pd.Timestamp):
            return obj.strftime('%d/%m/%Y')
        elif isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.strftime('%d/%m/%Y')
        elif hasattr(obj, 'to_json'):
            return obj.to_json()
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        return super().default(obj)

app = Flask(__name__)
CORS(app)
app.json_encoder = CustomJSONEncoder

# Configuration
UPLOAD_FOLDER = 'uploads'
CLEANED_FOLDER = 'cleaned'
ALLOWED_EXTENSIONS = {'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CLEANED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Data Cleaning API is running'})

@app.route('/api/upload', methods=['POST'])
def upload_and_clean():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file. Please upload a CSV file'}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        original_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
        file.save(original_path)
        
        # Get cleaning options from request
        cleaning_options = {
            'missing_strategy': request.form.get('missing_strategy', 'mean'),
            'fix_dtypes': request.form.get('fix_dtypes', 'true').lower() == 'true',
            'remove_duplicates': request.form.get('remove_duplicates', 'true').lower() == 'true',
            'trim_whitespace': request.form.get('trim_whitespace', 'true').lower() == 'true',
            'lowercase_text': request.form.get('lowercase_text', 'false').lower() == 'true',
            'detect_outliers': request.form.get('detect_outliers', 'true').lower() == 'true'
        }
        
        # Process the file using DataCleaningBot
        bot = DataCleaningBot(original_path)
        
        # Apply cleaning operations
        if cleaning_options['missing_strategy']:
            bot.handle_missing_values(strategy=cleaning_options['missing_strategy'])
        
        if cleaning_options['fix_dtypes']:
            bot.fix_dtypes()
        
        if cleaning_options['remove_duplicates']:
            bot.remove_duplicates()
        
        if cleaning_options['trim_whitespace']:
            bot.trim_whitespace()
        
        if cleaning_options['lowercase_text']:
            bot.lowercase_columns()
        
        if cleaning_options['detect_outliers']:
            bot.detect_outliers()
        
        # Save cleaned data
        cleaned_filename = f"cleaned_{file_id}_{filename}"
        cleaned_path = os.path.join(CLEANED_FOLDER, cleaned_filename)
        log_filename = f"log_{file_id}_{filename.replace('.csv', '.json')}"
        log_path = os.path.join(CLEANED_FOLDER, log_filename)
        
        bot.save_cleaned_data(cleaned_path)
        bot.save_log(log_path)
        
        # Get summary and preview
        summary = {
            'original_shape': bot.df.shape,
            'columns': bot.df.columns.tolist(),
            'dtypes': {col: str(dtype) for col, dtype in bot.df.dtypes.items()},
            'missing_values': bot.df.isnull().sum().to_dict(),
            'log': bot.log
        }
        
        preview_data = bot.df.head(10).to_dict('records')
        
        # Clean up original file
        os.remove(original_path)
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'summary': summary,
            'preview': preview_data,
            'cleaned_filename': cleaned_filename,
            'log_filename': log_filename,
            'message': 'File processed successfully!'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<file_type>/<file_id>/<filename>')
def download_file(file_type, file_id, filename):
    try:
        if file_type == 'csv':
            filepath = os.path.join(CLEANED_FOLDER, f"cleaned_{file_id}_{filename}")
        elif file_type == 'log':
            filepath = os.path.join(CLEANED_FOLDER, f"log_{file_id}_{filename.replace('.csv', '.json')}")
        else:
            return jsonify({'error': 'Invalid file type'}), 400
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(filepath, as_attachment=True)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
