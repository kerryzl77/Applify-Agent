from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash, send_from_directory
import os
import sys
import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from app.resume_parser import ResumeParser
from rq import Queue
from app.worker_config import redis_conn
from app.tasks import process_resume_task

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix imports to use relative imports instead of absolute imports
from scraper.retriever import DataRetriever
from database.db_manager import DatabaseManager
from app.llm_generator import LLMGenerator
from app.output_formatter import OutputFormatter

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.urandom(24)  # For session management

# Initialize components
data_retriever = DataRetriever()
db_manager = DatabaseManager()
llm_generator = LLMGenerator()
output_formatter = OutputFormatter()
resume_parser = ResumeParser()

# Initialize RQ queue
q = Queue(connection=redis_conn)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, result = db_manager.verify_user(email, password)
        
        if success:
            session['user_id'] = result
            return redirect(url_for('index'))
        else:
            flash(result, 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        success, result = db_manager.register_user(email, password)
        
        if success:
            session['user_id'] = result
            return redirect(url_for('index'))
        else:
            flash(result, 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/api/generate', methods=['POST'])
@login_required
def generate_content():
    """Generate content based on user input."""
    data = request.json
    
    # Get content type and input data
    content_type = data.get('content_type')
    url = data.get('url')
    manual_text = data.get('manual_text')
    input_type = data.get('input_type', 'url')  # 'url' or 'manual'
    user_job_title = data.get('job_title', '')
    user_company_name = data.get('company_name', '')
    
    # Validate input
    if not content_type or (not url and not manual_text):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get job/profile data based on input type
    if input_type == 'url':
        if 'linkedin.com' in url:
            job_data = data_retriever.scrape_linkedin_profile(url, user_job_title, user_company_name)
        else:
            job_data = data_retriever.scrape_job_posting(url, user_job_title, user_company_name)
    else:  # manual input
        if content_type == 'linkedin_message':
            job_data = data_retriever.parse_manual_linkedin_profile(manual_text, user_job_title, user_company_name)
        else:
            job_data = data_retriever.parse_manual_job_posting(manual_text, user_job_title, user_company_name)
    
    # Check if scraping was successful
    if 'error' in job_data:
        return jsonify({'error': f"Failed to scrape data: {job_data['error']}"}), 400
    
    # Get candidate data
    candidate_data = db_manager.get_candidate_data(session['user_id'])
    
    # Generate content based on type
    if content_type == 'linkedin_message':
        # For LinkedIn messages, we need both job data and profile data
        if input_type == 'manual':
            profile_data = data_retriever.parse_manual_linkedin_profile(manual_text, user_job_title, user_company_name)
        else:
            profile_data = data_retriever.scrape_linkedin_profile(url, user_job_title, user_company_name)
            
        # Check if profile data was successfully retrieved
        if 'error' in profile_data:
            return jsonify({'error': f"Failed to get profile data: {profile_data['error']}"}), 400
            
        content = llm_generator.generate_linkedin_message(job_data, candidate_data, profile_data)
    elif content_type == 'connection_email':
        # For connection emails, we need both job data and profile data
        if input_type == 'manual':
            profile_data = data_retriever.parse_manual_linkedin_profile(manual_text, user_job_title, user_company_name)
        else:
            profile_data = data_retriever.scrape_linkedin_profile(url, user_job_title, user_company_name)
            
        # Check if profile data was successfully retrieved
        if 'error' in profile_data:
            return jsonify({'error': f"Failed to get profile data: {profile_data['error']}"}), 400
            
        # Generate connection email with both job and profile data
        content = llm_generator.generate_connection_email(job_data, candidate_data, profile_data)
    elif content_type == 'hiring_manager_email':
        content = llm_generator.generate_hiring_manager_email(job_data, candidate_data)
    elif content_type == 'cover_letter':
        content = llm_generator.generate_cover_letter(job_data, candidate_data)
    else:
        return jsonify({'error': 'Invalid content type'}), 400
    
    # Format the content
    formatted_content = output_formatter.format_text(content, content_type)
    
    # Save generated content to database
    metadata = {
        'job_title': job_data.get('job_title', ''),
        'company_name': job_data.get('company_name', ''),
        'url': url,
        'generated_at': str(datetime.datetime.now()),
        'input_type': input_type
    }
    content_id = db_manager.save_generated_content(content_type, formatted_content, metadata, session['user_id'])
    
    # Create document file if needed
    file_info = None
    if content_type in ['cover_letter', 'connection_email', 'hiring_manager_email']:
        file_info = output_formatter.create_docx(formatted_content, job_data, candidate_data, content_type)
    
    # Return the generated content
    response = {
        'content': formatted_content,
        'content_id': content_id,
        'file_info': file_info
    }
    
    return jsonify(response)

@app.route('/api/download/<path:file_path>')
@login_required
def download_file(file_path):
    """Download a generated file."""
    try:
        # Get the file from the temp directory
        file_full_path = os.path.join(output_formatter.output_dir, file_path)
        
        # Check if file exists
        if not os.path.exists(file_full_path):
            return jsonify({'error': f'File not found: {file_path}'}), 404
            
        # Send the file
        return send_file(
            file_full_path,
            as_attachment=True,
            download_name=file_path,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

@app.route('/api/convert-to-pdf/<path:file_path>')
@login_required
def convert_to_pdf(file_path):
    """Convert a DOCX file to PDF and download it."""
    try:
        # Get the file from the temp directory
        docx_path = os.path.join(output_formatter.output_dir, file_path)
        
        # Check if source file exists
        if not os.path.exists(docx_path):
            return jsonify({'error': f'Source file not found: {file_path}'}), 404
        
        # Convert to PDF
        docx_info = {
            'filename': file_path,
            'filepath': docx_path
        }
        pdf_info = output_formatter.convert_to_pdf(docx_info)
        
        if pdf_info and os.path.exists(pdf_info['filepath']):
            return send_file(
                pdf_info['filepath'],
                as_attachment=True,
                download_name=pdf_info['filename'],
                mimetype='application/pdf'
            )
        else:
            error_msg = "PDF conversion failed. Please try downloading the DOCX file instead."
            return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        print(f"Error in convert_to_pdf: {str(e)}")
        return jsonify({'error': f'Error converting to PDF: {str(e)}'}), 500

@app.route('/api/candidate-data', methods=['GET'])
@login_required
def get_candidate_data():
    """Get candidate data for the frontend."""
    return jsonify(db_manager.get_candidate_data(session['user_id']))

@app.route('/api/update-candidate-data', methods=['POST'])
@login_required
def update_candidate_data():
    """Update candidate data."""
    data = request.json
    db_manager.update_candidate_data(data, session['user_id'])
    return jsonify({'success': True})

@app.route('/api/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    """Handle resume upload and start background processing."""
    if 'resume' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['resume']
    job_description = request.form.get('job_description', '')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        
        # Enqueue the job
        job = q.enqueue(
            process_resume_task,
            args=(upload_path, job_description),
            job_timeout='30m'
        )
        
        return jsonify({
            'message': 'Resume processing started',
            'job_id': job.id
        }), 202

@app.route('/api/resume-status/<job_id>', methods=['GET'])
@login_required
def get_resume_status(job_id):
    """Get the status of a resume processing job."""
    job = q.fetch_job(job_id)
    
    if job is None:
        return jsonify({'status': 'not_found'}), 404
        
    if job.is_failed:
        return jsonify({
            'status': 'failed',
            'error': str(job.exc_info)
        }), 500
        
    if job.is_finished:
        return jsonify({
            'status': 'completed',
            'result': job.result
        })
        
    return jsonify({'status': 'processing'})

@app.route('/api/candidate-data/<job_id>', methods=['GET'])
@login_required
def get_candidate_data_by_job(job_id):
    """Get candidate data for a specific job."""
    job = q.fetch_job(job_id)
    
    if job is None or not job.is_finished:
        return jsonify({'error': 'Job not found or not completed'}), 404
        
    if job.is_failed:
        return jsonify({'error': 'Job failed'}), 500
        
    return jsonify(job.result)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
 