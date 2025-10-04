from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash, send_from_directory, Response
from flask_cors import CORS
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

# Determine the correct paths for templates and static files
# Works both in development and production (Docker/Heroku)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIST = os.path.join(BASE_DIR, 'client', 'dist')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__,
            template_folder=TEMPLATES_DIR,
            static_folder=CLIENT_DIST,
            static_url_path='')

# CORS configuration for React frontend
# In production, specify allowed origins instead of "*"
allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*')
if allowed_origins != '*':
    allowed_origins = [origin.strip() for origin in allowed_origins.split(',')]
CORS(app, supports_credentials=True, origins=allowed_origins)

# Simple session configuration - use built-in Flask sessions
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.permanent_session_lifetime = datetime.timedelta(days=1)

# Security settings for production
is_production = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('HEROKU_APP_NAME')
if is_production:
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cross-site for API calls
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Let Flask handle domain
    logging.info("Production mode: Enhanced security settings enabled")
else:
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Dev environment

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
            return jsonify({'error': 'Unauthorized', 'message': 'Please log in'}), 401
        return f(*args, **kwargs)
    return decorated_function

# API Routes for Authentication
@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle user login via JSON API."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    success, result = db_manager.verify_user(email, password)

    if success:
        session['user_id'] = result
        session.permanent = True
        return jsonify({'success': True, 'user_id': result, 'message': 'Login successful'})
    else:
        return jsonify({'error': result}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    """Handle user registration via JSON API."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if not email or not password or not confirm_password:
        return jsonify({'error': 'All fields are required'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    success, result = db_manager.register_user(email, password)

    if success:
        session['user_id'] = result
        session.permanent = True
        return jsonify({'success': True, 'user_id': result, 'message': 'Registration successful'})
    else:
        return jsonify({'error': result}), 400

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Handle user logout via JSON API."""
    session.clear()
    return jsonify({'success': True, 'message': 'Logout successful'})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Check if user is authenticated."""
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'user_id': session['user_id']})
    else:
        return jsonify({'authenticated': False}), 401

@app.route('/api/generate', methods=['POST'])
@login_required
def generate_content():
    """Generate content based on user input with Redis caching."""
    data = request.json
    
    # Get content type and input data
    content_type = data.get('content_type')
    url = data.get('url')  # Primary URL (job posting or LinkedIn profile)
    linkedin_url = data.get('linkedin_url')  # Optional LinkedIn URL
    manual_text = data.get('manual_text')
    input_type = data.get('input_type', 'url')  # 'url' or 'manual'
    person_name = data.get('person_name', '')
    person_position = data.get('person_position', '')
    
    # Validate input
    connection_types = ['linkedin_message', 'connection_email', 'hiring_manager_email']
    needs_profile = content_type in connection_types
    
    if not content_type:
        return jsonify({'error': 'Missing content type'}), 400
    
    if needs_profile and input_type == 'url':
        # For connection messages, require person name and position
        if not person_name or not person_position:
            return jsonify({'error': 'Person name and position are required for connection messages'}), 400
    elif not url and not manual_text:
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
    
    # Create cache key data
    temp_job_data = {
        'person_name': person_name,
        'person_position': person_position,
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
    
    # Initialize job_data and profile_data
    job_data = None
    profile_data = None
    
    if input_type == 'url':
        if needs_profile:
            # For connection messages: use manual person name/position
            # Optionally try to enhance with LinkedIn data if URL provided
            profile_data = {
                'name': person_name,
                'title': person_position.split(' at ')[0] if ' at ' in person_position else person_position,
                'company': person_position.split(' at ')[1] if ' at ' in person_position else '',
                'location': '',
                'about': '',
                'experience': [],
                'education': [],
                'skills': [],
                'url': linkedin_url or ''
            }
            
            # Optionally try to scrape LinkedIn if URL provided (may fail with 451)
            if linkedin_url and 'linkedin.com/in/' in linkedin_url:
                try:
                    logging.info(f"Attempting to scrape LinkedIn profile: {linkedin_url}")
                    scraped_profile = data_retriever.scrape_linkedin_profile(linkedin_url)
                    
                    # If scraping succeeds, enhance profile_data
                    if scraped_profile and 'error' not in scraped_profile:
                        logging.info(f"LinkedIn scraping successful for {linkedin_url}")
                        # Merge scraped data with manual data (manual takes precedence)
                        profile_data['about'] = scraped_profile.get('about', '')
                        profile_data['experience'] = scraped_profile.get('experience', [])
                        profile_data['education'] = scraped_profile.get('education', [])
                        profile_data['skills'] = scraped_profile.get('skills', [])
                        if not profile_data['location']:
                            profile_data['location'] = scraped_profile.get('location', '')
                    else:
                        logging.warning(f"LinkedIn scraping failed for {linkedin_url}: {scraped_profile.get('error', 'Unknown error')}")
                except Exception as e:
                    logging.warning(f"LinkedIn scraping exception for {linkedin_url}: {str(e)}")
                    # Continue with manual data
            
            # Create minimal job context
            job_data = {
                'job_title': 'the position',
                'company_name': profile_data['company'] or 'the company',
                'job_description': f'Opportunity at {profile_data["company"] or "the company"}',
                'requirements': '',
                'url': linkedin_url or ''
            }
        else:
            # For cover letters: only need job posting
            if 'linkedin.com' in url:
                return jsonify({
                    'error': 'Cover letters require a job posting URL, not a LinkedIn profile',
                    'help': 'Please provide the job posting URL'
                }), 400
            job_data = data_retriever.scrape_job_posting(url)
            if 'error' in job_data:
                return jsonify({'error': f"Failed to get job posting: {job_data['error']}"}), 400
    else:  # manual input
        if needs_profile:
            # Parse manual LinkedIn profile info from text
            profile_data = data_retriever.parse_manual_linkedin_profile(manual_text)
            if 'error' in profile_data:
                return jsonify({'error': f"Failed to parse profile data: {profile_data['error']}"}), 400
            
            # Use person name/position if provided
            if person_name:
                profile_data['name'] = person_name
            if person_position:
                profile_data['title'] = person_position.split(' at ')[0] if ' at ' in person_position else person_position
                profile_data['company'] = person_position.split(' at ')[1] if ' at ' in person_position else ''
            
            # Create basic job data
            job_data = {
                'job_title': 'the position',
                'company_name': profile_data.get('company', 'the company'),
                'job_description': f'Opportunity at {profile_data.get("company", "the company")}',
                'requirements': '',
                'url': 'manual_input'
            }
        else:
            # Parse manual job posting
            job_data = data_retriever.parse_manual_job_posting(manual_text)
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
            args=(task_id, job_description, candidate_data, session['user_id'], url, output_formatter.output_dir)
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

def process_resume_refinement_background(task_id, job_description, candidate_data, user_id, job_url=None, output_dir=None):
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
        
        # Use advanced multi-agent resume generation system
        from app.advanced_resume_generator import AdvancedResumeGenerator
        
        def progress_wrapper(step, progress, message):
            update_progress(step, progress, message)
        
        generator = AdvancedResumeGenerator()
        
        update_progress('initializing_ai', 10, '🚀 Initializing 5-Agent AI System...')
        optimized_resume, metrics = generator.generate_optimized_resume(
            candidate_data, job_description, progress_wrapper
        )
        
        update_progress('generating_pdf', 75, 'Creating professional PDF (ultra-fast)...')
        # Use fast PDF generation instead of slow DOCX creation
        # CRITICAL FIX: Use global output_formatter instance to ensure files are saved 
        # to the same temp directory that the download endpoint uses
        
        # Extract job title from optimized resume metadata
        job_title = optimized_resume.get('metadata', {}).get('target_job', 'Position')
        
        # Create PDF directly using fast generator with global output_formatter
        pdf_result = output_formatter.create_resume_pdf_direct(
            optimized_resume, candidate_data, job_title
        )
        
        if not pdf_result:
            # Fallback to DOCX if PDF fails
            update_progress('formatting_docx', 80, 'Creating DOCX as fallback...')
            # Pass the global output_formatter's output_dir to ensure consistency
            formatted_resume = resume_refiner.create_formatted_resume_docx(
                optimized_resume, candidate_data, job_title, output_formatter.output_dir
            )
        else:
            formatted_resume = pdf_result
        
        if not formatted_resume:
            update_progress('error', 0, 'Failed to create formatted resume', 'error')
            return
        
        update_progress('completed', 100, '🎉 Advanced AI Resume Optimization Complete!', 'completed', {
            'file_info': {
                'filename': formatted_resume['filename'],
                'filepath': formatted_resume['filepath']
            },
            'advanced_metrics': {
                'ats_score': metrics.ats_score,
                'keyword_match_score': metrics.keyword_match_score,
                'content_quality_score': metrics.content_quality_score,
                'job_relevance_score': metrics.job_relevance_score,
                'word_count': metrics.estimated_word_count,
                'one_page_compliant': metrics.one_page_compliance,
                'generation_time': optimized_resume['metadata']['generation_time'],
                'ai_agents_used': 5
            },
            'optimization_details': {
                'target_job': optimized_resume['metadata']['target_job'],
                'optimization_level': 'Google-level Advanced',
                'ats_version': '2025',
                'strengths': metrics.strengths,
                'improvement_areas': metrics.improvement_areas[:3]
            },
            'recommendations': [
                f"🎯 Advanced AI Resume for: {optimized_resume['metadata']['target_job']}",
                f"🏆 ATS Score: {metrics.ats_score}/100 (Target: 75+)",
                f"🔍 Keyword Match: {metrics.keyword_match_score}/100",
                f"📝 Content Quality: {metrics.content_quality_score}/100",
                f"📄 Word Count: {metrics.estimated_word_count} ({'✅ One-page compliant' if metrics.one_page_compliance else '⚠️ May exceed one page'})",
                f"⚡ Generated in {optimized_resume['metadata']['generation_time']:.1f}s using 5 AI agents",
                "💾 Download your ATS-optimized resume below!"
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
        
        # Analyze job requirements (ultra-fast)
        job_analysis = resume_refiner.quick_job_analysis(job_description)
        
        # Analyze current resume (ultra-fast)
        resume_analysis = resume_refiner.quick_resume_analysis(candidate_data, job_analysis)
        
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

@app.route('/api/test-linkedin-scraper', methods=['POST'])
@login_required
def test_linkedin_scraper():
    """Test LinkedIn profile scraping with the new enterprise-grade scraper."""
    try:
        data = request.json
        linkedin_url = data.get('linkedin_url', '').strip()
        
        if not linkedin_url:
            return jsonify({'error': 'LinkedIn URL is required'}), 400
        
        # Validate LinkedIn URL format
        if not ('linkedin.com/in/' in linkedin_url):
            return jsonify({'error': 'Please provide a valid LinkedIn profile URL'}), 400
        
        # Import LinkedIn scraper
        from app.linkedin_scraper import LinkedInScraper
        scraper = LinkedInScraper()
        
        # Test API connections first
        connection_status = scraper.test_connection()
        
        # Extract profile data
        profile = scraper.extract_profile_data(linkedin_url)
        
        if not profile:
            return jsonify({
                'success': False,
                'error': 'Failed to extract profile data',
                'connection_status': connection_status,
                'available_methods': {
                    'bright_data': bool(connection_status.get('bright_data')),
                    'rapidapi': bool(connection_status.get('rapidapi')),
                    'basic_parsing': bool(connection_status.get('basic_parsing'))
                }
            }), 400
        
        # Get job-relevant context
        job_description = data.get('job_description', '')
        context = scraper.get_job_relevant_context(profile, job_description)
        
        return jsonify({
            'success': True,
            'profile_data': {
                'name': profile.name,
                'current_position': profile.current_position,
                'current_company': profile.current_company,
                'location': profile.location,
                'headline': profile.headline,
                'about': profile.about[:300] + '...' if len(profile.about) > 300 else profile.about,
                'skills': profile.skills[:10],
                'experience_count': len(profile.experience),
                'education_count': len(profile.education),
                'extracted_keywords': profile.extracted_keywords
            },
            'job_context': context,
            'connection_status': connection_status,
            'scraping_method': 'enterprise_api'
        })
        
    except Exception as e:
        logging.error(f"LinkedIn scraper test error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Scraper test failed: {str(e)}'
        }), 500

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

# Serve React App - MUST BE LAST to not interfere with API routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """Serve React app for all non-API routes."""
    # Skip API routes - return 404
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404

    # Serve static files
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)

    # Serve index.html for all other routes (React Router)
    index_path = os.path.join(app.static_folder, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(app.static_folder, 'index.html')
    else:
        logging.error(f"index.html not found at {index_path}")
        logging.error(f"static_folder: {app.static_folder}")
        logging.error(f"BASE_DIR: {BASE_DIR}")
        logging.error(f"Files in static_folder: {os.listdir(app.static_folder) if os.path.exists(app.static_folder) else 'Directory does not exist'}")
        return jsonify({'error': 'Frontend not found', 'static_folder': app.static_folder}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
 