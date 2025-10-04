const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Flask backend URL
const FLASK_BACKEND = process.env.FLASK_BACKEND_URL || 'http://localhost:5001';

// Security middleware
app.use(helmet({
  contentSecurityPolicy: false, // Allow inline scripts for development
  crossOriginEmbedderPolicy: false
}));

// Compression middleware
app.use(compression());

// CORS configuration
app.use(cors({
  origin: process.env.NODE_ENV === 'production'
    ? process.env.FRONTEND_URL
    : 'http://localhost:5173',
  credentials: true
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/api/', limiter);

// Body parser
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Proxy API requests to Flask backend
app.use('/api', createProxyMiddleware({
  target: FLASK_BACKEND,
  changeOrigin: true,
  onProxyReq: (proxyReq, req, res) => {
    // Forward cookies and session data
    if (req.headers.cookie) {
      proxyReq.setHeader('Cookie', req.headers.cookie);
    }
  },
  onProxyRes: (proxyRes, req, res) => {
    // Forward set-cookie headers
    if (proxyRes.headers['set-cookie']) {
      res.setHeader('Set-Cookie', proxyRes.headers['set-cookie']);
    }
  },
  logLevel: 'debug'
}));

// Proxy auth routes to Flask backend
app.use('/login', createProxyMiddleware({
  target: FLASK_BACKEND,
  changeOrigin: true
}));

app.use('/register', createProxyMiddleware({
  target: FLASK_BACKEND,
  changeOrigin: true
}));

app.use('/logout', createProxyMiddleware({
  target: FLASK_BACKEND,
  changeOrigin: true
}));

// Serve static files from React build in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, 'client/dist')));

  // Handle React routing - return all requests to React app
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'client/dist', 'index.html'));
  });
}

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Server Error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

app.listen(PORT, () => {
  console.log(`🚀 Node.js proxy server running on port ${PORT}`);
  console.log(`🔗 Proxying API requests to: ${FLASK_BACKEND}`);
  console.log(`📦 Environment: ${process.env.NODE_ENV || 'development'}`);
});

module.exports = app;
