# Job Application Assistant

A tool to automate the creation of tailored job application materials using LLMs.

## Features

- Generate LinkedIn connection messages (200 characters)
- Create connection emails (200 words)
- Write emails to hiring managers (200 words)
- Produce cover letters (350 words)
- Automatically scrape job postings and LinkedIn profiles
- Store and manage your personal information, resume, and story bank
- Export documents as DOCX or PDF

## Setup

### Prerequisites

- Python 3.9+
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/job-application-llm.git
   cd job-application-llm
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

### Running the Application

Start the Flask server:
   ```
   bash
   python -m app.app
   ```

Then open your browser and navigate to `http://localhost:5000`.

### Using Docker

You can also run the application using Docker:

1. Build the Docker image:
   ```bash
   docker build -t job-application-llm .
   ```

2. Run the container:
   ```bash
   docker run -p 5000:5000 -e OPENAI_API_KEY=your_api_key_here job-application-llm
   ```

3. Access the application at `http://localhost:5000`.

## Usage

1. Enter your personal information, resume details, and stories in the profile section.
2. Paste a job posting URL or LinkedIn profile URL.
3. Select the type of content you want to generate.
4. Click "Generate" and wait for the result.
5. Copy the generated text or download it as a DOCX/PDF file.

## Project Structure

- `app/`: Flask application code
- `scraper/`: Data retriever module
- `templates/`: HTML templates
- `static/`: CSS and JavaScript files
- `database/`: Candidate data storage
- `output/`: Generated DOCX/PDF files
