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
    
    // Functions
    function handleGenerate(e) {
        e.preventDefault();
        
        const contentType = document.getElementById('contentType').value;
        const jobUrl = document.getElementById('jobUrl').value;
        
        if (!contentType || !jobUrl) {
            showError('Please select a content type and enter a job URL.');
            return;
        }
        
        // Show loading indicator
        initialMessage.classList.add('d-none');
        resultContent.classList.add('d-none');
        errorMessage.classList.add('d-none');
        loadingIndicator.classList.remove('d-none');
        downloadButtons.classList.add('d-none');
        
        // Make API request
        fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content_type: contentType,
                url: jobUrl
            })
        })
        .then(response => response.json())
        .then(data => {
            loadingIndicator.classList.add('d-none');
            
            if (data.error) {
                showError(data.error);
                return;
            }
            
            // Display the generated content
            generatedText.textContent = data.content;
            resultContent.classList.remove('d-none');
            
            // Show download buttons if file was generated
            if (data.file_path) {
                currentFilePath = data.file_path;
                downloadButtons.classList.remove('d-none');
                downloadDocxBtn.classList.remove('d-none');
                downloadPdfBtn.classList.remove('d-none');
            } else {
                downloadDocxBtn.classList.add('d-none');
                downloadPdfBtn.classList.add('d-none');
                copyBtn.classList.remove('d-none');
                downloadButtons.classList.remove('d-none');
            }
            
            // Update history
            loadGenerationHistory();
        })
        .catch(error => {
            loadingIndicator.classList.add('d-none');
            showError('An error occurred: ' + error.message);
        });
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
            window.location.href = '/api/download/' + currentFilePath;
        }
    }
    
    function downloadPdf() {
        if (currentFilePath) {
            window.location.href = '/api/convert-to-pdf/' + currentFilePath;
        }
    }
    
    function loadCandidateData() {
        fetch('/api/candidate-data')
            .then(response => response.json())
            .then(data => {
                candidateData = data;
                updateCandidateDisplay();
                populateProfileForm();
                loadGenerationHistory();
            })
            .catch(error => {
                console.error('Error loading candidate data:', error);
            });
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
            templates: candidateData.templates,
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
}); 