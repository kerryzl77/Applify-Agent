import axios from 'axios';

// Get API base URL from environment variables or use default
// In production, use empty string to make requests to the same origin (Flask serves both frontend and API)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
  withCredentials: true, // Enable sending cookies for session management
});

// Request interceptor (no token needed - using Flask sessions)
api.interceptors.request.use(
  (config) => {
    // No need to add Authorization header - using Flask sessions with cookies
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error
      const { status, data } = error.response;

      // Don't auto-redirect on 401 from /api/auth/check to prevent infinite loops
      // The App.jsx component handles authentication checking gracefully
      if (status === 401 && !error.config.url.includes('/api/auth/check')) {
        // Only redirect to login for other 401 errors (session expired during use)
        // And only if we're not already on login/register page
        if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
          window.location.href = '/login';
        }
      }

      return Promise.reject({
        message: data.error || data.message || 'An error occurred',
        status,
        data,
      });
    } else if (error.request) {
      // Request made but no response
      return Promise.reject({
        message: 'No response from server. Please check your connection.',
        status: 0,
      });
    } else {
      // Something else happened
      return Promise.reject({
        message: error.message || 'An unexpected error occurred',
        status: 0,
      });
    }
  }
);

// Authentication endpoints
export const authAPI = {
  register: async (userData) => {
    const response = await api.post('/api/register', userData);
    return response.data;
  },

  login: async (credentials) => {
    const response = await api.post('/api/login', credentials);
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/api/logout');
    return response.data;
  },

  check: async () => {
    const response = await api.get('/api/auth/check');
    return response.data;
  },

  getProfile: async () => {
    const response = await api.get('/api/candidate-data');
    return response.data;
  },

  updateProfile: async (profileData) => {
    const response = await api.post('/api/update-candidate-data', profileData);
    return response.data;
  },
};

// Profile management endpoints
export const profileAPI = {
  get: async () => {
    const response = await api.get('/api/candidate-data');
    return response.data;
  },

  update: async (profileData) => {
    const response = await api.post('/api/update-candidate-data', profileData);
    return response.data;
  },

  delete: async () => {
    const response = await api.delete('/api/candidate-data');
    return response.data;
  },
};

// Resume upload endpoints
export const resumeAPI = {
  upload: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('resume', file);

    const response = await api.post('/api/upload-resume', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onUploadProgress(percentCompleted);
        }
      },
    });

    return response.data;
  },

  get: async () => {
    const response = await api.get('/api/candidate-data');
    return response.data;
  },

  delete: async () => {
    const response = await api.delete('/api/candidate-data');
    return response.data;
  },
};

// Content generation endpoints
export const contentAPI = {
  generateCoverLetter: async (jobDescription, additionalInfo) => {
    const response = await api.post('/api/generate', {
      content_type: 'cover_letter',
      job_description: jobDescription,
      additional_info: additionalInfo,
    });
    return response.data;
  },

  generateEmail: async (purpose, recipient, context) => {
    const response = await api.post('/api/generate', {
      content_type: 'connection_email',
      purpose,
      recipient,
      context,
    });
    return response.data;
  },

  generateResumeTailored: async (jobDescription) => {
    const response = await api.post('/api/refine-resume', {
      job_description: jobDescription,
      input_type: 'manual'
    });
    return response.data;
  },

  improveContent: async (content, contentType, feedback) => {
    const response = await api.post('/api/generate', {
      content,
      content_type: contentType,
      feedback,
    });
    return response.data;
  },

  // Generic generation endpoint for chat-like interface
  generate: async (type, data) => {
    const response = await api.post('/api/generate', data);
    return response.data;
  },
};

export const gmailAPI = {
  status: async () => {
    const response = await api.get('/api/gmail/status');
    return response.data;
  },

  getAuthUrl: async () => {
    const response = await api.get('/api/gmail/auth-url');
    return response.data;
  },

  createDraft: async (payload) => {
    const response = await api.post('/api/gmail/create-draft', payload);
    return response.data;
  },

  disconnect: async () => {
    const response = await api.post('/api/gmail/disconnect');
    return response.data;
  },

  uploadClient: async (file) => {
    const formData = new FormData();
    formData.append('client', file);
    const response = await api.post('/api/gmail/client', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  deleteClient: async () => {
    const response = await api.delete('/api/gmail/client');
    return response.data;
  },
};

// Job application tracking endpoints (if needed in future)
export const applicationAPI = {
  getAll: async () => {
    const response = await api.get('/applications');
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/applications/${id}`);
    return response.data;
  },

  create: async (applicationData) => {
    const response = await api.post('/applications', applicationData);
    return response.data;
  },

  update: async (id, applicationData) => {
    const response = await api.put(`/applications/${id}`, applicationData);
    return response.data;
  },

  delete: async (id) => {
    const response = await api.delete(`/applications/${id}`);
    return response.data;
  },
};

// Health check endpoint
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
