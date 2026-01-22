import axios from 'axios';

// Get API base URL from environment variables or use default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Token storage keys
const ACCESS_TOKEN_KEY = 'applify_access_token';
const REFRESH_TOKEN_KEY = 'applify_refresh_token';

// Token management utilities
export const tokenManager = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  
  setTokens: (accessToken, refreshToken) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  
  clearTokens: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
  
  hasTokens: () => !!localStorage.getItem(ACCESS_TOKEN_KEY),
};

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Request interceptor - add Authorization header
api.interceptors.request.use(
  (config) => {
    const token = tokenManager.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response) {
      const { status, data } = error.response;
      
      // Handle 401 - try to refresh token
      if (status === 401 && !originalRequest._retry) {
        // Don't retry refresh or auth check endpoints
        if (originalRequest.url.includes('/api/auth/refresh') || 
            originalRequest.url.includes('/api/auth/check')) {
          tokenManager.clearTokens();
          if (!window.location.pathname.includes('/login') && 
              !window.location.pathname.includes('/register')) {
            window.location.href = '/login';
          }
          return Promise.reject(error);
        }
        
        if (isRefreshing) {
          // Wait for the refresh to complete
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          }).then(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          }).catch(err => {
            return Promise.reject(err);
          });
        }
        
        originalRequest._retry = true;
        isRefreshing = true;
        
        const refreshToken = tokenManager.getRefreshToken();
        
        if (!refreshToken) {
          tokenManager.clearTokens();
          isRefreshing = false;
          if (!window.location.pathname.includes('/login') && 
              !window.location.pathname.includes('/register')) {
            window.location.href = '/login';
          }
          return Promise.reject(error);
        }
        
        try {
          const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token, refresh_token } = response.data;
          tokenManager.setTokens(access_token, refresh_token);
          
          processQueue(null, access_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          
          return api(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          tokenManager.clearTokens();
          if (!window.location.pathname.includes('/login') && 
              !window.location.pathname.includes('/register')) {
            window.location.href = '/login';
          }
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }
      
      return Promise.reject({
        message: data.detail || data.error || data.message || 'An error occurred',
        status,
        data,
      });
    } else if (error.request) {
      return Promise.reject({
        message: 'No response from server. Please check your connection.',
        status: 0,
      });
    } else {
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
    const response = await api.post('/api/auth/register', userData);
    const { access_token, refresh_token } = response.data;
    tokenManager.setTokens(access_token, refresh_token);
    return response.data;
  },

  login: async (credentials) => {
    const response = await api.post('/api/auth/login', credentials);
    const { access_token, refresh_token } = response.data;
    tokenManager.setTokens(access_token, refresh_token);
    return { success: true, ...response.data };
  },

  logout: async () => {
    try {
      await api.post('/api/auth/logout');
    } catch {
      // Ignore errors - we're logging out anyway
    }
    tokenManager.clearTokens();
    return { success: true };
  },

  check: async () => {
    if (!tokenManager.hasTokens()) {
      return { authenticated: false };
    }
    try {
      const response = await api.get('/api/auth/check');
      return response.data;
    } catch {
      return { authenticated: false };
    }
  },

  getProfile: async () => {
    const response = await api.get('/api/content/candidate-data');
    return response.data;
  },

  updateProfile: async (profileData) => {
    const response = await api.post('/api/content/candidate-data', profileData);
    return response.data;
  },
};

// Profile management endpoints
export const profileAPI = {
  get: async () => {
    const response = await api.get('/api/content/candidate-data');
    return response.data;
  },

  update: async (profileData) => {
    const response = await api.post('/api/content/candidate-data', profileData);
    return response.data;
  },

  delete: async () => {
    const response = await api.delete('/api/content/candidate-data');
    return response.data;
  },
};

// Resume upload endpoints
export const resumeAPI = {
  upload: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('resume', file);

    const response = await api.post('/api/resume/upload', formData, {
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
    const response = await api.get('/api/content/candidate-data');
    return response.data;
  },

  getProgress: async () => {
    const response = await api.get('/api/resume/progress');
    return response.data;
  },

  clearProgress: async () => {
    const response = await api.post('/api/resume/clear-progress');
    return response.data;
  },
};

// Content generation endpoints
export const contentAPI = {
  generateCoverLetter: async (jobDescription, additionalInfo) => {
    const response = await api.post('/api/content/generate', {
      content_type: 'cover_letter',
      manual_text: jobDescription,
      input_type: 'manual',
      additional_info: additionalInfo,
    });
    return response.data;
  },

  generateEmail: async (purpose, recipient, context) => {
    const response = await api.post('/api/content/generate', {
      content_type: 'connection_email',
      purpose,
      recipient,
      context,
    });
    return response.data;
  },

  generateResumeTailored: async (jobDescription) => {
    const response = await api.post('/api/resume/refine', {
      job_description: jobDescription,
      input_type: 'manual'
    });
    return response.data;
  },

  improveContent: async (content, contentType, feedback) => {
    const response = await api.post('/api/content/generate', {
      content,
      content_type: contentType,
      feedback,
    });
    return response.data;
  },

  generate: async (type, data) => {
    const response = await api.post('/api/content/generate', data);
    return response.data;
  },

  validateUrl: async (url) => {
    const response = await api.post('/api/content/validate-url', { url });
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
};

// Health check endpoint
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
