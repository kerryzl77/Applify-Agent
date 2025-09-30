from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash, send_from_directory, Response
import os
import sys
import datetime
import logging
import json
import time
import uuid
import threading
from functools import wraps
from werkzeug.utils import secure_filename
from app.resume_parser import ResumeParser
from app.background_tasks import BackgroundProcessor
from app.enhanced_resume_processor import enhanced_resume_processor
from app.redis_manager import RedisManager
from app.resume_refiner import ResumeRefiner

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix imports to use relative imports instead of absolute imports
from scraper.retriever import DataRetriever
from scraper.url_validator import URLValidator
from database.db_manager import DatabaseManager
from app.cached_llm import CachedLLMGenerator
from app.output_formatter import OutputFormatter

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Simple session configuration - use built-in Flask sessions
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.permanent_session_lifetime = datetime.timedelta(days=1)

# Initialize Redis for caching only, not sessions
redis_manager = RedisManager()
if redis_manager.is_available():
    logging.info("Redis available for caching")
else:
    logging.warning("Redis unavailable, caching disabled")

# Initialize components
data_retriever = DataRetriever()
url_validator = URLValidator()
db_manager = DatabaseManager()
llm_generator = CachedLLMGenerator()
output_formatter = OutputFormatter()
resume_parser = ResumeParser()
background_processor = BackgroundProcessor()
resume_refiner = ResumeRefiner()

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
    """Handle user logout."""
    session.clear()  # Clear all session data
    return redirect(url_for('login'))

@app.route('/api/generate', methods=['POST'])
@login_required
def generate_content():
    """Generate content based on user input with Redis caching."""
    data = request.json
    
    # Get content type and input data
    content_type = data.get('content_type')
    url = data.get('url')  # Primary URL (job posting or profile)
    profile_url = data.get('profile_url')  # Secondary URL for LinkedIn profile (connection messages)
    job_url = data.get('job_url')  # Secondary URL for job posting (when profile_url is primary)
    manual_text = data.get('manual_text')
    input_type = data.get('input_type', 'url')  # 'url' or 'manual'
    user_job_title = data.get('job_title', '')
    user_company_name = data.get('company_name', '')
    
    # Validate input
    if not content_type or (not url and not manual_text):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate URL if provided
    if input_type == 'url' and url:
        url_validation = url_validator.validate_and_parse_url(url)
        if not url_validation['valid']:
            return jsonify({
                'error': f"Invalid URL: {url_validation['error']}",
                'recommendations': url_validator.get_url_recommendations(url_validation['type'])
            }), 400
        
        # Check for warnings
        if 'warning' in url_validation:
            # Log warning but continue processing
            logging.warning(f"URL warning for {url}: {url_validation['warning']}")
        
        # Update URL if normalized
        url = url_validation['url']
    
    # Create job data for cache key generation
    temp_job_data = {
        'company_name': user_company_name,
        'job_title': user_job_title,
        'url': url or 'manual_input'
    }
    
    # Check cache first
    cached_content = redis_manager.get_cached_content(content_type, temp_job_data, session['user_id'])
    if cached_content:
        logging.info(f"Cache hit for content generation: {content_type}")
        return jsonify({
            'content': cached_content['content'],
            'cached': True,
            'generated_at': cached_content.get('generated_at')
        })
    
    # Get candidate data first
    candidate_data = db_manager.get_candidate_data(session['user_id'])
    
    # Determine if this content type needs both job and profile data
    connection_types = ['linkedin_message', 'connection_email', 'hiring_manager_email']
    needs_profile = content_type in connection_types
    
    # Initialize job_data and profile_data
    job_data = None
    profile_data = None
    
    if input_type == 'url':
        if needs_profile:
            # For connection messages: need BOTH job posting and LinkedIn profile
            # Try to intelligently determine URLs
            if profile_url:
                # Two URLs provided (ideal case)
                actual_job_url = job_url or url
                actual_profile_url = profile_url
            elif 'linkedin.com/in/' in url:
                # Only LinkedIn profile provided - use job title/company for job context
                actual_profile_url = url
                actual_job_url = None
                job_data = {
                    'job_title': user_job_title or 'the position',
                    'company_name': user_company_name or 'the company',
                    'job_description': f'Opportunity at {user_company_name or "the company"} for {user_job_title or "the position"}',
                    'requirements': '',
                    'url': url
                }
            else:
                # Job posting URL provided - need LinkedIn profile too
                return jsonify({
                    'error': f'{content_type.replace("_", " ").title()} requires a LinkedIn profile URL',
                    'help': 'Please provide the LinkedIn profile URL of the person you want to contact',
                    'example': 'https://linkedin.com/in/person-name'
                }), 400
            
            # Scrape LinkedIn profile
            if actual_profile_url:
                profile_data = data_retriever.scrape_linkedin_profile(actual_profile_url, user_job_title, user_company_name)
                if 'error' in profile_data:
                    return jsonify({'error': f"Failed to get LinkedIn profile: {profile_data['error']}"}), 400
            
            # Scrape job posting if not already set
            if not job_data and actual_job_url:
                job_data = data_retriever.scrape_job_posting(actual_job_url, user_job_title, user_company_name)
                if 'error' in job_data:
                    return jsonify({'error': f"Failed to get job posting: {job_data['error']}"}), 400
        else:
            # For cover letters: only need job posting
            if 'linkedin.com' in url:
                return jsonify({
                    'error': 'Cover letters require a job posting URL, not a LinkedIn profile',
                    'help': 'Please provide the job posting URL'
                }), 400
            job_data = data_retriever.scrape_job_posting(url, user_job_title, user_company_name)
            if 'error' in job_data:
                return jsonify({'error': f"Failed to get job posting: {job_data['error']}"}), 400
    else:  # manual input
        if needs_profile:
            # Parse manual LinkedIn profile info
            profile_data = data_retriever.parse_manual_linkedin_profile(manual_text, user_job_title, user_company_name)
            if 'error' in profile_data:
                return jsonify({'error': f"Failed to parse profile data: {profile_data['error']}"}), 400
            # Create basic job data from user inputs
            job_data = {
                'job_title': user_job_title or 'the position',
                'company_name': user_company_name or 'the company',
                'job_description': f'Opportunity at {user_company_name or "the company"}',
                'requirements': '',
                'url': 'manual_input'
            }
        else:
            # Parse manual job posting
            job_data = data_retriever.parse_manual_job_posting(manual_text, user_job_title, user_company_name)
            if 'error' in job_data:
                return jsonify({'error': f"Failed to parse job posting: {job_data['error']}"}), 400
    
    # Generate content based on type (job_data and profile_data already prepared above)
    if content_type == 'linkedin_message':
        content = llm_generator.generate_linkedin_message(job_data, candidate_data, profile_data)
    elif content_type == 'connection_email':
        content = llm_generator.generate_connection_email(job_data, candidate_data, profile_data)
    elif content_type == 'hiring_manager_email':
        content = llm_generator.generate_hiring_manager_email(job_data, candidate_data, profile_data)
    elif content_type == 'cover_letter':
        content = llm_generator.generate_cover_letter(job_data, candidate_data)
    else:
        return jsonify({'error': 'Invalid content type'}), 400
    
    # Format the content
    formatted_content = output_formatter.format_text(content, content_type)
    
    # Cache the generated content
    redis_manager.cache_generated_content(content_type, formatted_content, job_data, session['user_id'])
    
    # Save generated content to database
    metadata = {
        'job_title': job_data.get('job_title', ''),
        'company_name': job_data.get('company_name', ''),
        'url': url,
        'generated_at': str(datetime.datetime.now()),
        'input_type': input_type
    }
    content_id = db_manager.save_generated_content(content_type, formatted_content, metadata, session['user_id'])
    
    # Create document file if needed - do this immediately for better UX
    file_info = None
    if content_type in ['cover_letter', 'connection_email', 'hiring_manager_email']:
        try:
            file_info = output_formatter.create_docx(formatted_content, job_data, candidate_data, content_type)
            if file_info:
                logging.info(f"Document created successfully: {file_info['filename']}")
        except Exception as e:
            logging.error(f"Error creating document: {str(e)}")
            file_info = None
    
    # Return the generated content
    response = {
        'content': formatted_content,
        'content_id': content_id,
        'file_info': file_info,
        'cached': False
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
    """Get candidate data for the frontend with caching."""
    cache_key = f"candidate_data:{session['user_id']}"
    cached_data = redis_manager.get(cache_key)
    
    if cached_data:
        return jsonify(cached_data)
    
    data = db_manager.get_candidate_data(session['user_id'])
    redis_manager.set(cache_key, data, 300)  # Cache for 5 minutes
    return jsonify(data)

@app.route('/api/update-candidate-data', methods=['POST'])
@login_required
def update_candidate_data():
    """Update candidate data and invalidate cache."""
    data = request.json
    db_manager.update_candidate_data(data, session['user_id'])
    
    # Invalidate user cache when profile is updated
    redis_manager.invalidate_user_cache(session['user_id'])
    
    return jsonify({'success': True})

@app.route('/api/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    """Enhanced resume upload with progress tracking and caching."""
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['resume']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'.pdf', '.docx'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File type {file_ext} not supported. Please upload PDF or DOCX files only.'}), 400
        
        # Validate file size (10MB max)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 400
        
        if file_size < 1000:  # 1KB minimum
            return jsonify({'error': 'File too small. Please upload a valid resume file.'}), 400
            
        # Save the uploaded file
        try:
            file_path = resume_parser.save_uploaded_file(file)
        except Exception as e:
            return jsonify({'error': f'Error saving file: {str(e)}'}), 500
            
        # Start enhanced background processing
        enhanced_resume_processor.start_processing(file_path, session['user_id'], file.filename)
        
        return jsonify({
            'status': 'queued',
            'message': 'Resume queued for processing. Check progress with /api/resume-progress',
            'filename': file.filename,
            'size': file_size
        })
        
    except Exception as e:
        logging.error(f"Upload error for user {session.get('user_id')}: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/resume-progress')
@login_required
def get_resume_progress():
    """Get detailed resume processing progress."""
    try:
        status = enhanced_resume_processor.get_status(session['user_id'])
        return jsonify(status)
    except Exception as e:
        logging.error(f"Progress check error for user {session.get('user_id')}: {str(e)}")
        return jsonify({'error': 'Failed to get progress'}), 500

@app.route('/api/clear-resume-progress', methods=['POST'])
@login_required
def clear_resume_progress():
    """Clear resume processing status."""
    try:
        enhanced_resume_processor.clear_status(session['user_id'])
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Clear progress error for user {session.get('user_id')}: {str(e)}")
        return jsonify({'error': 'Failed to clear progress'}), 500

@app.route('/api/validate-url', methods=['POST'])
@login_required
def validate_url():
    """Validate URL and provide feedback to user."""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate the URL
        validation_result = url_validator.validate_and_parse_url(url)
        
        # Add recommendations for invalid or warning cases
        if not validation_result['valid'] or 'warning' in validation_result:
            validation_result['recommendations'] = url_validator.get_url_recommendations(validation_result['type'])
        
        return jsonify(validation_result)
        
    except Exception as e:
        logging.error(f"URL validation error: {str(e)}")
        return jsonify({'error': 'Failed to validate URL'}), 500

@app.route('/api/resume-progress/<task_id>')
@login_required
def resume_progress_stream(task_id):
    """Server-sent events for resume refinement progress."""
    def generate():
        progress_key = f"resume_progress:{session['user_id']}:{task_id}"
        last_progress = 0
        
        while True:
            try:
                progress_data = redis_manager.get(progress_key)
                if progress_data:
                    current_progress = progress_data.get('progress', 0)
                    if current_progress > last_progress or progress_data.get('status') in ['completed', 'error']:
                        yield f"data: {json.dumps(progress_data)}\n\n"
                        last_progress = current_progress
                        
                        if progress_data.get('status') in ['completed', 'error']:
                            break
                
                time.sleep(0.5)  # Check every 500ms
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"
                break
    
    return Response(generate(), mimetype='text/plain')

@app.route('/api/refine-resume', methods=['POST'])
@login_required 
def refine_resume():
    """Refine resume based on job description - starts background processing."""
    try:
        data = request.json
        job_description = data.get('job_description', '').strip()
        input_type = data.get('input_type', 'manual')  # 'url' or 'manual'
        url = data.get('url', '') if input_type == 'url' else None
        
        if not job_description and not url:
            return jsonify({'error': 'Job description or URL is required'}), 400
        
        # Get candidate data first to validate
        candidate_data = db_manager.get_candidate_data(session['user_id'])
        if not candidate_data or not candidate_data.get('resume'):
            return jsonify({'error': 'Please upload your resume first before refining it'}), 400
        
        # Get job description from URL if needed
        if input_type == 'url' and url:
            # Validate URL first
            url_validation = url_validator.validate_and_parse_url(url)
            if not url_validation['valid']:
                return jsonify({
                    'error': f"Invalid URL: {url_validation['error']}",
                    'recommendations': url_validator.get_url_recommendations(url_validation['type'])
                }), 400
            
            # Scrape job posting (quick operation)
            job_data = data_retriever.scrape_job_posting(url)
            if 'error' in job_data:
                return jsonify({'error': f"Failed to fetch job description: {job_data['error']}"}), 400
            job_description = job_data.get('job_description', '') + "\n\n" + job_data.get('requirements', '')
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Start background processing
        thread = threading.Thread(
            target=process_resume_refinement_background,
            args=(task_id, job_description, candidate_data, session['user_id'], url)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediately with task ID
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': 'processing',
            'message': 'Resume refinement started. Check progress with task_id.'
        })
        
    except Exception as e:
        logging.error(f"Resume refinement error for user {session.get('user_id')}: {str(e)}")
        return jsonify({'error': f'Failed to start resume refinement: {str(e)}'}), 500

def process_resume_refinement_background(task_id, job_description, candidate_data, user_id, job_url=None):
    """Background task for resume refinement with progress tracking."""
    progress_key = f"resume_refinement:{user_id}:{task_id}"
    
    def update_progress(step, progress, message, status='processing', data=None):
        """Update progress in Redis."""
        progress_data = {
            'task_id': task_id,
            'step': step,
            'progress': progress,
            'message': message,
            'status': status,
            'timestamp': datetime.datetime.now().isoformat(),
            'data': data or {}
        }
        redis_manager.set(progress_key, progress_data, ttl=1800)  # 30 min TTL
        logging.info(f"Resume refinement progress [{user_id}]: {step} - {progress}% - {message}")
    
    try:
        update_progress('initializing', 5, 'Starting resume refinement...')
        
        update_progress('analyzing_job', 15, 'Analyzing job requirements...')
        job_analysis = resume_refiner.analyze_job_requirements(job_description)
        
        update_progress('analyzing_resume', 30, 'Analyzing your current resume...')
        resume_analysis = resume_refiner.analyze_current_resume(candidate_data)
        
        update_progress('optimizing', 50, 'Optimizing resume content with AI...')
        optimized_resume = resume_refiner.generate_optimized_resume(
            candidate_data, job_analysis, resume_analysis
        )
        
        update_progress('formatting', 75, 'Creating professionally formatted document...')
        formatted_resume = resume_refiner.create_formatted_resume_docx(
            optimized_resume, candidate_data, job_analysis.get('job_title', 'Position')
        )
        
        if not formatted_resume:
            update_progress('error', 0, 'Failed to create formatted resume', 'error')
            return
        
        update_progress('completed', 100, 'Resume refinement completed successfully!', 'completed', {
            'file_info': {
                'filename': formatted_resume['filename'],
                'filepath': formatted_resume['filename']
            },
            'analysis': {
                'job_title': job_analysis.get('job_title', ''),
                'optimization_score': optimized_resume['optimization_score'],
                'word_count': optimized_resume['word_count'],
                'template_used': job_analysis.get('resume_template', 'business')
            },
            'recommendations': [
                f"✅ Resume optimized for {job_analysis.get('job_title', 'the position')}",
                f"📊 Optimization score: {optimized_resume['optimization_score']}/100",
                f"📝 Word count: {optimized_resume['word_count']} words",
                f"🎯 Template: {job_analysis.get('resume_template', 'business').title()}",
                "💾 Download your tailored resume below!"
            ]
        })
        
    except Exception as e:
        logging.error(f"Resume refinement background error for user {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        update_progress('error', 0, f'Error: {str(e)}', 'error')

@app.route('/api/resume-refinement-progress/<task_id>')
@login_required
def get_refinement_progress(task_id):
    """Get progress of resume refinement task."""
    try:
        progress_key = f"resume_refinement:{session['user_id']}:{task_id}"
        progress_data = redis_manager.get(progress_key)
        
        if not progress_data:
            return jsonify({
                'status': 'not_found',
                'message': 'No refinement task found with this ID'
            }), 404
        
        return jsonify(progress_data)
    except Exception as e:
        logging.error(f"Error getting refinement progress: {str(e)}")
        return jsonify({'error': 'Failed to get progress'}), 500

@app.route('/api/resume-analysis', methods=['POST'])
@login_required 
def analyze_resume():
    """Analyze current resume without refinement."""
    try:
        data = request.json
        job_description = data.get('job_description', '').strip()
        
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        
        # Get candidate data
        candidate_data = db_manager.get_candidate_data(session['user_id'])
        if not candidate_data or not candidate_data.get('resume'):
            return jsonify({'error': 'Please upload your resume first'}), 400
        
        # Analyze job requirements
        job_analysis = resume_refiner.analyze_job_requirements(job_description)
        
        # Analyze current resume
        resume_analysis = resume_refiner.analyze_current_resume(candidate_data)
        
        # Calculate match score
        match_score = resume_refiner._calculate_optimization_score(job_analysis, resume_analysis)
        
        return jsonify({
            'analysis': {
                'job_requirements': {
                    'job_title': job_analysis.get('job_title'),
                    'required_skills': job_analysis.get('required_skills', []),
                    'preferred_skills': job_analysis.get('preferred_skills', []),
                    'key_qualifications': job_analysis.get('key_qualifications', []),
                    'important_keywords': job_analysis.get('important_keywords', [])
                },
                'resume_assessment': {
                    'current_strengths': resume_analysis.get('current_strengths', []),
                    'improvement_areas': resume_analysis.get('improvement_areas', []),
                    'keyword_gaps': resume_analysis.get('keyword_gaps', []),
                    'skills_match': resume_analysis.get('skills_match', 'medium'),
                    'ats_score': resume_analysis.get('ats_optimization_score', 70)
                },
                'match_score': match_score,
                'recommendations': [
                    f"Overall match score: {match_score}/100",
                    f"Skills alignment: {resume_analysis.get('skills_match', 'medium')}",
                    "Consider using the resume refinement feature for optimization"
                ]
            }
        })
        
    except Exception as e:
        logging.error(f"Resume analysis error for user {session.get('user_id')}: {str(e)}")
        return jsonify({'error': f'Failed to analyze resume: {str(e)}'}), 500

# Keep legacy endpoint for backward compatibility
@app.route('/api/processing-status')
@login_required
def check_processing_status():
    """Legacy processing status endpoint."""
    return get_resume_progress()

@app.route('/health')
def health_check():
    """Health check endpoint for container monitoring."""
    try:
        # Check database connection
        try:
            conn = db_manager._get_connection()
            if conn:
                db_manager._return_connection(conn)
                db_healthy = True
            else:
                db_healthy = False
        except:
            db_healthy = False
        
        # Check Redis connection
        redis_healthy = redis_manager.is_available()
        
        status = {
            'status': 'healthy' if db_healthy and redis_healthy else 'unhealthy',
            'database': 'up' if db_healthy else 'down',
            'redis': 'up' if redis_healthy else 'down',
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        return jsonify(status), 200 if status['status'] == 'healthy' else 503
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 503

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
 