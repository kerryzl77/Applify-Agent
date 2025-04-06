// DOM Elements
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const errorMessage = document.getElementById('errorMessage');

// Event Listeners
if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
}
if (registerForm) {
    registerForm.addEventListener('submit', handleRegister);
}

// Handle login form submission
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'email': email,
                'password': password
            })
        });
        
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            const data = await response.json();
            showError(data.error || 'Login failed');
        }
    } catch (error) {
        showError('An error occurred during login');
    }
}

// Handle registration form submission
async function handleRegister(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    
    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return;
    }
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'email': email,
                'password': password,
                'confirm_password': confirmPassword
            })
        });
        
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            const data = await response.json();
            showError(data.error || 'Registration failed');
        }
    } catch (error) {
        showError('An error occurred during registration');
    }
}

// Show error message
function showError(message) {
    if (errorMessage) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('d-none');
    }
} 