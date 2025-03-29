from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import datetime
import json  # Add this import for pretty printing

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix imports to use relative imports instead of absolute imports
from scraper.retriever import DataRetriever
from database.db_manager import DatabaseManager
from app.llm_generator import LLMGenerator
from app.output_formatter import OutputFormatter

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Initialize components
data_retriever = DataRetriever()
db_manager = DatabaseManager()
llm_generator = LLMGenerator()
output_formatter = OutputFormatter()

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_content():
    """Generate content based on user input."""
    data = request.json
    
    # Get content type and URL
    content_type = data.get('content_type')
    url = data.get('url')
    
    # Validate input
    if not content_type or not url:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Debug log
    print(f"\n\n===== Processing URL: {url} =====")
    print(f"Content type: {content_type}")
    
    # Scrape data from URL
    if 'linkedin.com' in url:
        print("Detected LinkedIn URL, scraping profile...")
        job_data = data_retriever.scrape_linkedin_profile(url)
    else:
        print("Scraping job posting...")
        job_data = data_retriever.scrape_job_posting(url)
    
    # Debug log - print the job data
    print("\n===== Scraped Data =====")
    print(json.dumps(job_data, indent=2))
    print("========================\n")
    
    # Check if scraping was successful
    if 'error' in job_data:
        print(f"Error during scraping: {job_data['error']}")
        return jsonify({'error': f"Failed to scrape data: {job_data['error']}"}), 400
    
    # Get candidate data
    candidate_data = db_manager.get_candidate_data()
    
    # Generate content based on type
    print(f"Generating {content_type}...")
    if content_type == 'linkedin_message':
        content = llm_generator.generate_linkedin_message(job_data, candidate_data)
    elif content_type == 'connection_email':
        content = llm_generator.generate_connection_email(job_data, candidate_data)
    elif content_type == 'hiring_manager_email':
        content = llm_generator.generate_hiring_manager_email(job_data, candidate_data)
    elif content_type == 'cover_letter':
        content = llm_generator.generate_cover_letter(job_data, candidate_data)
    else:
        print(f"Invalid content type: {content_type}")
        return jsonify({'error': 'Invalid content type'}), 400
    
    # Format the content
    formatted_content = output_formatter.format_text(content, content_type)
    
    # Save generated content to database
    metadata = {
        'job_title': job_data.get('job_title', ''),
        'company_name': job_data.get('company_name', ''),
        'url': url,
        'generated_at': str(datetime.datetime.now())
    }
    content_id = db_manager.save_generated_content(content_type, formatted_content, metadata)
    
    # Create document file if needed
    file_path = None
    if content_type in ['cover_letter', 'connection_email', 'hiring_manager_email']:
        file_path = output_formatter.create_docx(formatted_content, job_data, candidate_data, content_type)
    
    # Return the generated content
    response = {
        'content': formatted_content,
        'content_id': content_id,
        'file_path': file_path
    }
    
    print(f"Successfully generated {content_type}")
    return jsonify(response)

@app.route('/api/download/<path:file_path>')
def download_file(file_path):
    """Download a generated file."""
    directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    return send_file(os.path.join(directory, file_path), as_attachment=True)

@app.route('/api/convert-to-pdf/<path:file_path>')
def convert_to_pdf(file_path):
    """Convert a DOCX file to PDF and download it."""
    directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    docx_path = os.path.join(directory, file_path)
    
    # Convert to PDF
    pdf_path = output_formatter.convert_to_pdf(docx_path)
    
    if pdf_path:
        return send_file(pdf_path, as_attachment=True)
    else:
        return jsonify({'error': 'Failed to convert to PDF'}), 500

@app.route('/api/candidate-data')
def get_candidate_data():
    """Get candidate data for the frontend."""
    return jsonify(db_manager.get_candidate_data())

@app.route('/api/update-candidate-data', methods=['POST'])
def update_candidate_data():
    """Update candidate data."""
    data = request.json
    db_manager.update_candidate_data(data)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 