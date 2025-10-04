import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, File, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import useStore from '../store/useStore';
import { resumeAPI } from '../services/api';
import { formatFileSize } from '../utils/helpers';
import toast from 'react-hot-toast';

const ResumeUploader = ({ onUploadComplete }) => {
  const { setResume, setResumeUploading } = useStore();
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, success, error

  const allowedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.pdf',
    '.doc',
    '.docx',
  ];

  const validateFile = (file) => {
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!file) {
      toast.error('Please select a file');
      return false;
    }

    if (file.size > maxSize) {
      toast.error('File size must be less than 10MB');
      return false;
    }

    const isValidType = allowedTypes.some(type => {
      if (type.startsWith('.')) {
        return file.name.toLowerCase().endsWith(type);
      }
      return file.type === type;
    });

    if (!isValidType) {
      toast.error('Please upload a PDF or Word document');
      return false;
    }

    return true;
  };

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && validateFile(droppedFile)) {
      setFile(droppedFile);
    }
  }, []);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && validateFile(selectedFile)) {
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploadStatus('uploading');
    setResumeUploading(true);
    setUploadProgress(0);

    try {
      const response = await resumeAPI.upload(file, (progress) => {
        setUploadProgress(progress);
      });

      setUploadStatus('success');
      setResume(response.resume);
      toast.success('Resume uploaded successfully!');

      if (onUploadComplete) {
        onUploadComplete(response.resume);
      }

      // Reset after success
      setTimeout(() => {
        setFile(null);
        setUploadProgress(0);
        setUploadStatus('idle');
      }, 2000);
    } catch (error) {
      setUploadStatus('error');
      toast.error(error.message || 'Failed to upload resume');
      setTimeout(() => {
        setUploadStatus('idle');
        setUploadProgress(0);
      }, 2000);
    } finally {
      setResumeUploading(false);
    }
  };

  const handleRemove = () => {
    setFile(null);
    setUploadProgress(0);
    setUploadStatus('idle');
  };

  return (
    <div className="w-full">
      <AnimatePresence mode="wait">
        {!file ? (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`
              relative border-2 border-dashed rounded-xl p-8 transition-all duration-200
              ${
                isDragging
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
              }
            `}
          >
            <input
              type="file"
              id="resume-upload"
              className="hidden"
              accept={allowedTypes.join(',')}
              onChange={handleFileSelect}
            />

            <label
              htmlFor="resume-upload"
              className="flex flex-col items-center cursor-pointer"
            >
              <motion.div
                animate={{ y: isDragging ? -10 : 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              >
                <Upload className={`w-12 h-12 mb-4 ${isDragging ? 'text-blue-500' : 'text-gray-400'}`} />
              </motion.div>

              <p className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
                {isDragging ? 'Drop your resume here' : 'Upload your resume'}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Drag and drop or click to browse
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500">
                Supports PDF, DOC, DOCX (Max 10MB)
              </p>
            </label>
          </motion.div>
        ) : (
          <motion.div
            key="file-preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="card p-6"
          >
            {/* File info */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start space-x-3">
                <div className="p-3 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                  <File className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>

              {uploadStatus === 'idle' && (
                <button
                  onClick={handleRemove}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Upload progress */}
            {uploadStatus === 'uploading' && (
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Uploading...</span>
                  <span className="text-gray-900 dark:text-gray-100 font-medium">
                    {uploadProgress}%
                  </span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-blue-600 to-purple-600"
                    initial={{ width: 0 }}
                    animate={{ width: `${uploadProgress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            )}

            {/* Status messages */}
            {uploadStatus === 'success' && (
              <div className="flex items-center space-x-2 text-green-600 dark:text-green-400 mb-4">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">Upload successful!</span>
              </div>
            )}

            {uploadStatus === 'error' && (
              <div className="flex items-center space-x-2 text-red-600 dark:text-red-400 mb-4">
                <AlertCircle className="w-5 h-5" />
                <span className="text-sm font-medium">Upload failed. Please try again.</span>
              </div>
            )}

            {/* Upload button */}
            {uploadStatus === 'idle' && (
              <motion.button
                onClick={handleUpload}
                className="w-full btn btn-primary flex items-center justify-center space-x-2"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Upload className="w-4 h-4" />
                <span>Upload Resume</span>
              </motion.button>
            )}

            {uploadStatus === 'uploading' && (
              <button
                disabled
                className="w-full btn btn-primary flex items-center justify-center space-x-2 opacity-50 cursor-not-allowed"
              >
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Uploading...</span>
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ResumeUploader;
