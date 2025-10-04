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
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
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

      if (status === 401) {
        // Unauthorized - clear local storage and redirect to login
        localStorage.removeItem('token');
        window.location.href = '/login';
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
    const response = await api.post('/auth/register', userData);
    return response.data;
  },

  login: async (credentials) => {
    const response = await api.post('/auth/login', credentials);
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },

  getProfile: async () => {
    const response = await api.get('/auth/profile');
    return response.data;
  },

  updateProfile: async (profileData) => {
    const response = await api.put('/auth/profile', profileData);
    return response.data;
  },
};

// Profile management endpoints
export const profileAPI = {
  get: async () => {
    const response = await api.get('/profile');
    return response.data;
  },

  update: async (profileData) => {
    const response = await api.put('/profile', profileData);
    return response.data;
  },

  delete: async () => {
    const response = await api.delete('/profile');
    return response.data;
  },
};

// Resume upload endpoints
export const resumeAPI = {
  upload: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('resume', file);

    const response = await api.post('/resume/upload', formData, {
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
    const response = await api.get('/resume');
    return response.data;
  },

  delete: async () => {
    const response = await api.delete('/resume');
    return response.data;
  },
};

// Content generation endpoints
export const contentAPI = {
  generateCoverLetter: async (jobDescription, additionalInfo) => {
    const response = await api.post('/generate/cover-letter', {
      job_description: jobDescription,
      additional_info: additionalInfo,
    });
    return response.data;
  },

  generateEmail: async (purpose, recipient, context) => {
    const response = await api.post('/generate/email', {
      purpose,
      recipient,
      context,
    });
    return response.data;
  },

  generateResumeTailored: async (jobDescription) => {
    const response = await api.post('/generate/resume', {
      job_description: jobDescription,
    });
    return response.data;
  },

  improveContent: async (content, contentType, feedback) => {
    const response = await api.post('/generate/improve', {
      content,
      content_type: contentType,
      feedback,
    });
    return response.data;
  },

  // Generic generation endpoint for chat-like interface
  generate: async (type, data) => {
    const response = await api.post(`/generate/${type}`, data);
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
