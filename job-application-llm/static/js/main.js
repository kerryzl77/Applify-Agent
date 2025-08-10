document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const generateForm = document.getElementById('generateForm');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultContent = document.getElementById('resultContent');
    const initialMessage = document.getElementById('initialMessage');
    const errorMessage = document.getElementById('errorMessage');
    const generatedText = document.getElementById('generatedText');
    const downloadButtons = document.getElementById('downloadButtons');
    const copyBtn = document.getElementById('copyBtn');
    const downloadDocxBtn = document.getElementById('downloadDocxBtn');
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    const historyList = document.getElementById('historyList');
    const noHistoryMessage = document.getElementById('noHistoryMessage');
    
    // Profile elements
    const candidateName = document.getElementById('candidateName');
    const candidateRole = document.getElementById('candidateRole');
    const candidateSkills = document.getElementById('candidateSkills');
    const profileForm = document.getElementById('profileForm');
    const saveProfileBtn = document.getElementById('saveProfileBtn');
    
    // Current state
    let currentFilePath = null;
    let candidateData = null;
    
    // Add to the top of the file, after DOM Elements
    const logoutButton = document.getElementById('logoutButton');
    
    // Load candidate data
    loadCandidateData();
    
    // Event listeners
    generateForm.addEventListener('submit', handleGenerate);
    copyBtn.addEventListener('click', copyToClipboard);
    downloadDocxBtn.addEventListener('click', downloadDocx);
    downloadPdfBtn.addEventListener('click', downloadPdf);
    saveProfileBtn.addEventListener('click', saveProfile);
    
    document.getElementById('addExperienceBtn').addEventListener('click', addExperienceItem);
    document.getElementById('addEducationBtn').addEventListener('click', addEducationItem);
    document.getElementById('addStoryBtn').addEventListener('click', addStoryItem);
    
    // Enhanced resume upload functionality
    const resumeUpload = document.getElementById('resumeUpload');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressDetails = document.getElementById('progressDetails');
    
    if (resumeUpload) {
        resumeUpload.addEventListener('change', handleResumeUpload);
    }
    
    // Input type toggle handling
    const urlInput = document.getElementById('urlInput');
    const manualInput = document.getElementById('manualInput');
    const urlInputGroup = document.getElementById('urlInputGroup');
    const manualInputGroup = document.getElementById('manualInputGroup');

    urlInput.addEventListener('change', toggleInputType);
    manualInput.addEventListener('change', toggleInputType);

    function toggleInputType() {
        if (urlInput.checked) {
            urlInputGroup.classList.remove('d-none');
            manualInputGroup.classList.add('d-none');
            jobUrl.required = true;
            manualText.required = false;
        } else {
            urlInputGroup.classList.add('d-none');
            manualInputGroup.classList.remove('d-none');
            jobUrl.required = false;
            manualText.required = true;
        }
    }
    
    // Event Listeners
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }
    
    // Add event listener for resume upload
    document.getElementById('uploadResumeBtn').addEventListener('click', handleResumeUpload);
    
    // Functions
    async function handleGenerate(e) {
        e.preventDefault();
        
        const contentType = document.getElementById('contentType').value;
        const inputType = document.querySelector('input[name="inputType"]:checked').value;
        const jobUrl = document.getElementById('jobUrl').value;
        const manualText = document.getElementById('manualText').value;
        const jobTitle = document.getElementById('jobTitle').value;
        const companyName = document.getElementById('companyName').value;
        
        if (!contentType || (inputType === 'url' && !jobUrl) || (inputType === 'manual' && !manualText)) {
            showError('Please fill in all required fields.');
            return;
        }
        
        // Show loading indicator
        initialMessage.classList.add('d-none');
        resultContent.classList.add('d-none');
        errorMessage.classList.add('d-none');
        loadingIndicator.classList.remove('d-none');
        downloadButtons.classList.add('d-none');
        
        // Make API request
        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content_type: contentType,
                    input_type: inputType,
                    url: jobUrl,
                    manual_text: manualText,
                    job_title: jobTitle,
                    company_name: companyName
                })
            });
            
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            
            const result = await response.json();
            if (result.error) {
                throw new Error(result.error);
            }
            
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
            
            // Display the generated content immediately
            generatedText.textContent = result.content;
            resultContent.classList.remove('d-none');
            
            // Show download buttons if file was generated
            if (result.file_info) {
                currentFilePath = result.file_info.filename;
                
                // Show download buttons immediately
                downloadButtons.classList.remove('d-none');
                downloadDocxBtn.classList.remove('d-none');
                downloadPdfBtn.classList.remove('d-none');
                
                // Show immediate feedback that document is ready
                showSuccess('✅ Content generated! DOCX ready for download. PDF conversion available.');
            } else {
                downloadDocxBtn.classList.add('d-none');
                downloadPdfBtn.classList.add('d-none');
                copyBtn.classList.remove('d-none');
                downloadButtons.classList.remove('d-none');
                
                // Show feedback for non-document content
                showSuccess('✅ Content generated successfully!');
            }
            
            // Update history
            loadGenerationHistory();
        } catch (error) {
            loadingIndicator.classList.add('d-none');
            if (error.message === 'Unauthorized') {
                window.location.href = '/login';
            } else {
                showError('Error generating content: ' + error.message);
            }
        }
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('d-none');
    }
    
    function copyToClipboard() {
        navigator.clipboard.writeText(generatedText.textContent)
            .then(() => {
                // Show temporary success message
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            })
            .catch(err => {
                showError('Failed to copy: ' + err);
            });
    }
    
    function downloadDocx() {
        if (currentFilePath) {
            downloadFile({ filename: currentFilePath });
        }
    }
    
    function downloadPdf() {
        if (currentFilePath) {
            convertToPdf({ filename: currentFilePath });
        }
    }
    
    async function loadCandidateData() {
        try {
            const response = await fetch('/api/candidate-data');
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            candidateData = data;
            updateCandidateDisplay();
            populateProfileForm();
            loadGenerationHistory();
        } catch (error) {
            console.error('Error loading candidate data:', error);
            if (error.message === 'Unauthorized') {
                window.location.href = '/login';
            }
        }
    }
    
    function updateCandidateDisplay() {
        if (candidateData) {
            candidateName.textContent = candidateData.personal_info.name || 'Not set';
            
            const experience = candidateData.resume.experience;
            if (experience && experience.length > 0) {
                candidateRole.textContent = `${experience[0].title} at ${experience[0].company}`;
            } else {
                candidateRole.textContent = 'Not set';
            }
            
            const skills = candidateData.resume.skills;
            if (skills && skills.length > 0) {
                candidateSkills.textContent = skills.slice(0, 3).join(', ');
                if (skills.length > 3) {
                    candidateSkills.textContent += '...';
                }
            } else {
                candidateSkills.textContent = 'Not set';
            }
        }
    }
    
    function populateProfileForm() {
        if (!candidateData) return;
        
        // Personal info
        document.getElementById('name').value = candidateData.personal_info.name || '';
        document.getElementById('email').value = candidateData.personal_info.email || '';
        document.getElementById('phone').value = candidateData.personal_info.phone || '';
        document.getElementById('linkedin').value = candidateData.personal_info.linkedin || '';
        document.getElementById('github').value = candidateData.personal_info.github || '';
        
        // Resume
        document.getElementById('summary').value = candidateData.resume.summary || '';
        document.getElementById('skills').value = candidateData.resume.skills ? candidateData.resume.skills.join(', ') : '';
        
        // Experience
        const experienceContainer = document.getElementById('experienceContainer');
        experienceContainer.innerHTML = '';
        if (candidateData.resume.experience && candidateData.resume.experience.length > 0) {
            candidateData.resume.experience.forEach((exp, index) => {
                addExperienceItem(null, exp, index);
            });
        }
        
        // Education
        const educationContainer = document.getElementById('educationContainer');
        educationContainer.innerHTML = '';
        if (candidateData.resume.education && candidateData.resume.education.length > 0) {
            candidateData.resume.education.forEach((edu, index) => {
                addEducationItem(null, edu, index);
            });
        }
        
        // Story bank
        const storyBankContainer = document.getElementById('storyBankContainer');
        storyBankContainer.innerHTML = '';
        if (candidateData.story_bank && candidateData.story_bank.length > 0) {
            candidateData.story_bank.forEach((story, index) => {
                addStoryItem(null, story, index);
            });
        }
        
        // Templates
        const templateTypes = ['connection_emails', 'cover_letters', 'hiring_manager_emails', 'linkedin_messages'];
        templateTypes.forEach(type => {
            const containerId = `${type.replace('_', '')}Container`;
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = ''; // Clear existing content
                const templateData = candidateData.templates && candidateData.templates[type] ? candidateData.templates[type] : { title: '', template: '' };
                addTemplateItem(type, templateData);
            }
        });
    }
    
    function addExperienceItem(e, data = null, index = null) {
        const container = document.getElementById('experienceContainer');
        const itemIndex = index !== null ? index : container.children.length;
        
        const itemDiv = document.createElement('div');
        itemDiv.className = 'experience-item';
        itemDiv.dataset.index = itemIndex;
        
        itemDiv.innerHTML = `
            <span class="remove-btn" onclick="removeItem(this, 'experience')">&times;</span>
            <div class="row mb-2">
                <div class="col-md-6">
                    <label class="form-label">Job Title</label>
                    <input type="text" class="form-control" name="experience[${itemIndex}][title]" value="${data ? data.title : ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Company</label>
                    <input type="text" class="form-control" name="experience[${itemIndex}][company]" value="${data ? data.company : ''}">
                </div>
            </div>
            <div class="row mb-2">
                <div class="col-md-6">
                    <label class="form-label">Location</label>
                    <input type="text" class="form-control" name="experience[${itemIndex}][location]" value="${data ? data.location : ''}">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Start Date</label>
                    <input type="text" class="form-control" name="experience[${itemIndex}][start_date]" placeholder="YYYY-MM" value="${data ? data.start_date : ''}">
                </div>
                <div class="col-md-3">
                    <label class="form-label">End Date</label>
                    <input type="text" class="form-control" name="experience[${itemIndex}][end_date]" placeholder="YYYY-MM or Present" value="${data ? data.end_date : ''}">
                </div>
            </div>
            <div class="mb-2">
                <label class="form-label">Description</label>
                <textarea class="form-control" name="experience[${itemIndex}][description]" rows="2">${data ? data.description : ''}</textarea>
            </div>
        `;
        
        container.appendChild(itemDiv);
    }
    
    function addEducationItem(e, data = null, index = null) {
        const container = document.getElementById('educationContainer');
        const itemIndex = index !== null ? index : container.children.length;
        
        const itemDiv = document.createElement('div');
        itemDiv.className = 'education-item';
        itemDiv.dataset.index = itemIndex;
        
        itemDiv.innerHTML = `
            <span class="remove-btn" onclick="removeItem(this, 'education')">&times;</span>
            <div class="row mb-2">
                <div class="col-md-6">
                    <label class="form-label">Degree</label>
                    <input type="text" class="form-control" name="education[${itemIndex}][degree]" value="${data ? data.degree : ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Institution</label>
                    <input type="text" class="form-control" name="education[${itemIndex}][institution]" value="${data ? data.institution : ''}">
                </div>
            </div>
            <div class="row mb-2">
                <div class="col-md-6">
                    <label class="form-label">Location</label>
                    <input type="text" class="form-control" name="education[${itemIndex}][location]" value="${data ? data.location : ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Graduation Date</label>
                    <input type="text" class="form-control" name="education[${itemIndex}][graduation_date]" placeholder="YYYY-MM" value="${data ? data.graduation_date : ''}">
                </div>
            </div>
        `;
        
        container.appendChild(itemDiv);
    }
    
    function addStoryItem(e, data = null, index = null) {
        const container = document.getElementById('storyBankContainer');
        const itemIndex = index !== null ? index : container.children.length;
        
        const itemDiv = document.createElement('div');
        itemDiv.className = 'story-item';
        itemDiv.dataset.index = itemIndex;
        
        itemDiv.innerHTML = `
            <span class="remove-btn" onclick="removeItem(this, 'story')">&times;</span>
            <div class="mb-2">
                <label class="form-label">Title</label>
                <input type="text" class="form-control" name="story_bank[${itemIndex}][title]" value="${data ? data.title : ''}">
            </div>
            <div class="mb-2">
                <label class="form-label">Content</label>
                <textarea class="form-control" name="story_bank[${itemIndex}][content]" rows="3">${data ? data.content : ''}</textarea>
            </div>
        `;
        
        container.appendChild(itemDiv);
    }
    
    function addTemplateItem(type, data = null) {
        const containerMap = {
            'connection_emails': 'connectionEmailContainer',
            'cover_letters': 'coverLetterContainer',
            'hiring_manager_emails': 'hiringManagerEmailContainer',
            'linkedin_messages': 'linkedinMessageContainer'
        };
        
        const container = document.getElementById(containerMap[type]);
        container.innerHTML = '';  // Clear any existing template
        
        const itemDiv = document.createElement('div');
        itemDiv.className = 'template-item mb-3 border p-3 position-relative';
        itemDiv.dataset.type = type;
        
        itemDiv.innerHTML = `
            <div class="mb-2">
                <label class="form-label">Title</label>
                <input type="text" class="form-control" name="templates[${type}][title]" 
                    value="${data ? data.title : ''}">
            </div>
            <div class="mb-2">
                <label class="form-label">Template Content</label>
                <textarea class="form-control" name="templates[${type}][template]" 
                    rows="5" placeholder="Enter template with placeholders like {{name}}, {{company}}, etc.">${data ? data.template : ''}</textarea>
            </div>
        `;
        
        container.appendChild(itemDiv);
    }
    
    // Make removeItem function available globally
    window.removeItem = function(element, type) {
        const itemDiv = element.parentNode;
        itemDiv.parentNode.removeChild(itemDiv);
    };
    
    function saveProfile() {
        // Collect form data
        const formData = {
            personal_info: {
                name: document.getElementById('name').value,
                email: document.getElementById('email').value,
                phone: document.getElementById('phone').value,
                linkedin: document.getElementById('linkedin').value,
                github: document.getElementById('github').value
            },
            resume: {
                summary: document.getElementById('summary').value,
                experience: [],
                education: [],
                skills: document.getElementById('skills').value.split(',').map(s => s.trim()).filter(s => s)
            },
            story_bank: [],
            templates: {
                connection_emails: {
                    title: "",
                    template: ""
                },
                cover_letters: {
                    title: "",
                    template: ""
                },
                hiring_manager_emails: {
                    title: "",
                    template: ""
                },
                linkedin_messages: {
                    title: "",
                    template: ""
                }
            },
            generated_content: candidateData.generated_content
        };
        
        // Collect experience items
        const experienceItems = document.querySelectorAll('.experience-item');
        experienceItems.forEach(item => {
            const index = item.dataset.index;
            const experience = {
                title: item.querySelector(`input[name="experience[${index}][title]"]`).value,
                company: item.querySelector(`input[name="experience[${index}][company]"]`).value,
                location: item.querySelector(`input[name="experience[${index}][location]"]`).value,
                start_date: item.querySelector(`input[name="experience[${index}][start_date]"]`).value,
                end_date: item.querySelector(`input[name="experience[${index}][end_date]"]`).value,
                description: item.querySelector(`textarea[name="experience[${index}][description]"]`).value
            };
            formData.resume.experience.push(experience);
        });
        
        // Collect education items
        const educationItems = document.querySelectorAll('.education-item');
        educationItems.forEach(item => {
            const index = item.dataset.index;
            const education = {
                degree: item.querySelector(`input[name="education[${index}][degree]"]`).value,
                institution: item.querySelector(`input[name="education[${index}][institution]"]`).value,
                location: item.querySelector(`input[name="education[${index}][location]"]`).value,
                graduation_date: item.querySelector(`input[name="education[${index}][graduation_date]"]`).value
            };
            formData.resume.education.push(education);
        });
        
        // Collect story items
        const storyItems = document.querySelectorAll('.story-item');
        storyItems.forEach(item => {
            const index = item.dataset.index;
            const story = {
                title: item.querySelector(`input[name="story_bank[${index}][title]"]`).value,
                content: item.querySelector(`textarea[name="story_bank[${index}][content]"]`).value
            };
            formData.story_bank.push(story);
        });
        
        // Collect template items
        const containerMap = {
            'connection_emails': 'connectionEmailContainer',
            'cover_letters': 'coverLetterContainer',
            'hiring_manager_emails': 'hiringManagerEmailContainer',
            'linkedin_messages': 'linkedinMessageContainer'
        };
        
        Object.entries(containerMap).forEach(([type, containerId]) => {
            const container = document.getElementById(containerId);
            if (container) {
                const titleInput = container.querySelector(`input[name="templates[${type}][title]"]`);
                const templateInput = container.querySelector(`textarea[name="templates[${type}][template]"]`);
                
                if (titleInput && templateInput) {
                    formData.templates[type] = {
                        title: titleInput.value,
                        template: templateInput.value
                    };
                }
            }
        });
        
        // Save to server
        fetch('/api/update-candidate-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update local data
                candidateData = formData;
                updateCandidateDisplay();
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('profileModal'));
                modal.hide();
            } else {
                showError('Failed to save profile data.');
            }
        })
        .catch(error => {
            showError('An error occurred: ' + error.message);
        });
    }
    
    function loadGenerationHistory() {
        if (!candidateData || !candidateData.generated_content) return;
        
        const history = candidateData.generated_content;
        historyList.innerHTML = '';
        
        if (history.length === 0) {
            noHistoryMessage.classList.remove('d-none');
            return;
        }
        
        noHistoryMessage.classList.add('d-none');
        
        // Sort by most recent first
        history.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        // Display the 5 most recent items
        history.slice(0, 5).forEach(item => {
            const historyItem = document.createElement('a');
            historyItem.className = 'list-group-item list-group-item-action history-item';
            historyItem.href = '#';
            
            const contentType = item.type.replace('_', ' ');
            const date = new Date(item.created_at).toLocaleDateString();
            
            historyItem.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${contentType.charAt(0).toUpperCase() + contentType.slice(1)}</h6>
                    <small>${date}</small>
                </div>
                <p class="mb-1">${item.metadata.company_name} - ${item.metadata.job_title}</p>
            `;
            
            historyItem.addEventListener('click', (e) => {
                e.preventDefault();
                generatedText.textContent = item.content;
                resultContent.classList.remove('d-none');
                initialMessage.classList.add('d-none');
                
                // Hide download buttons for history items
                downloadButtons.classList.add('d-none');
            });
            
            historyList.appendChild(historyItem);
        });
    }

    // Add this new function
    async function handleLogout(e) {
        e.preventDefault();
        try {
            const response = await fetch('/logout');
            if (response.redirected) {
                window.location.href = response.url;
            }
        } catch (error) {
            console.error('Error during logout:', error);
        }
    }

    // Enhanced Resume Upload with Real-time Progress
    async function handleResumeUpload() {
        const fileInput = document.getElementById('resumeUpload');
        const file = fileInput.files[0];
        
        if (!file) {
            showError('Please select a resume file');
            return;
        }

        // Client-side validation
        if (file.size > 10 * 1024 * 1024) {
            showError('File size must be less than 10MB');
            return;
        }

        if (file.size < 1000) {
            showError('File is too small. Please upload a valid resume.');
            return;
        }

        const allowedExtensions = ['.pdf', '.docx'];
        const fileExtension = file.name.toLowerCase().substr(file.name.lastIndexOf('.'));
        if (!allowedExtensions.includes(fileExtension)) {
            showError('Please upload a PDF or DOCX file only');
            return;
        }

        showProgressBar();
        updateProgress(0, 'uploading', 'Uploading resume...', `File: ${file.name} (${formatFileSize(file.size)})`);
        
        const formData = new FormData();
        formData.append('resume', file);
        
        try {
            // Upload file and start processing
            const response = await fetch('/api/upload-resume', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to upload resume');
            }
            
            const result = await response.json();
            updateProgress(5, 'queued', 'Resume uploaded successfully', 'Starting AI analysis...');
            
            // Start polling for detailed progress
            pollEnhancedProgress();
            
        } catch (error) {
            hideProgressBar();
            showError(error.message);
        }
    }

    async function pollEnhancedProgress() {
        try {
            const response = await fetch('/api/resume-progress');
            const status = await response.json();
            
            if (status.step === 'complete') {
                updateProgress(100, 'complete', 'Resume processed successfully!', 
                    status.data?.cached ? 'Used cached data for faster processing' : 'Profile updated with new information');
                
                // Wait a bit then hide progress and refresh profile
                setTimeout(() => {
                    hideProgressBar();
                    loadCandidateData(); // Refresh the profile data
                    showSuccess('Your profile has been updated with resume information!');
                }, 2000);
                
            } else if (status.step === 'error') {
                hideProgressBar();
                showError(status.message || 'Error processing resume');
                
            } else if (status.progress !== undefined) {
                // Update progress with detailed information
                updateProgress(
                    status.progress, 
                    status.step, 
                    status.message,
                    getProgressDetails(status.step, status.data)
                );
                
                // Continue polling if not complete
                setTimeout(pollEnhancedProgress, 1000);
            } else {
                // Continue polling if status is not clear
                setTimeout(pollEnhancedProgress, 2000);
            }
        } catch (error) {
            console.error('Error checking progress:', error);
            setTimeout(pollEnhancedProgress, 3000); // Retry in 3 seconds
        }
    }

    function showProgressBar() {
        if (uploadProgress) {
            uploadProgress.classList.remove('d-none');
        }
        if (initialMessage) {
            initialMessage.classList.add('d-none');
        }
        if (errorMessage) {
            errorMessage.classList.add('d-none');
        }
    }

    function hideProgressBar() {
        if (uploadProgress) {
            uploadProgress.classList.add('d-none');
        }
    }

    function updateProgress(percentage, step, message, details = '') {
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
            progressBar.textContent = `${percentage}%`;
        }
        
        if (progressText) {
            progressText.textContent = message;
        }
        
        if (progressDetails && details) {
            progressDetails.textContent = details;
        }

        // Update progress bar color based on status
        if (progressBar) {
            progressBar.className = 'progress-bar';
            if (step === 'error') {
                progressBar.classList.add('bg-danger');
            } else if (step === 'complete') {
                progressBar.classList.add('bg-success');
            } else if (step === 'ai_parsing') {
                progressBar.classList.add('bg-info');
            } else {
                progressBar.classList.add('bg-primary');
            }
        }
    }

    function getProgressDetails(step, data) {
        const details = {
            'initializing': 'Preparing for processing...',
            'analyzing': 'Examining file structure and content...',
            'cache_hit': 'Found previously processed resume data',
            'extracting': 'Reading text from your resume...',
            'text_extracted': data?.text_length ? `Extracted ${data.text_length} characters` : 'Text extraction complete',
            'ai_parsing': 'AI is analyzing your skills and experience...',
            'merging': 'Intelligently updating your profile...',
            'saving': 'Saving your updated profile...',
            'complete': 'All done! Your profile is updated.',
            'error': 'Something went wrong during processing'
        };
        return details[step] || 'Processing...';
    }

    function formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Byte';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    function showSuccess(message) {
        if (errorMessage) {
            errorMessage.className = 'alert alert-success';
            errorMessage.textContent = message;
            errorMessage.classList.remove('d-none');
            
            // Auto-hide success message after 5 seconds
            setTimeout(() => {
                errorMessage.classList.add('d-none');
            }, 5000);
        }
    }

    // Function to handle file downloads
    function downloadFile(fileInfo) {
        if (!fileInfo || !fileInfo.filename) {
            showError('No file available for download');
            return;
        }

        // Create a temporary link element
        const link = document.createElement('a');
        link.href = `/api/download/${fileInfo.filename}`;
        link.download = fileInfo.filename;
        link.target = '_blank';
        
        // Append to body, click, and remove
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Function to convert DOCX to PDF
    function convertToPdf(fileInfo) {
        if (!fileInfo || !fileInfo.filename) {
            showError('No file available for conversion');
            return;
        }

        // Create a temporary link element
        const link = document.createElement('a');
        link.href = `/api/convert-to-pdf/${fileInfo.filename}`;
        link.download = fileInfo.filename.replace('.docx', '.pdf');
        link.target = '_blank';
        
        // Append to body, click, and remove
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}); 