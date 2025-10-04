import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Settings, Upload, User } from 'lucide-react';
import useStore from '../store/useStore';
import Sidebar from '../components/Sidebar';
import ContentGenerator from '../components/ContentGenerator';
import ProfileModal from '../components/ProfileModal';
import ResumeUploader from '../components/ResumeUploader';
import axios from 'axios';
import toast from 'react-hot-toast';

const Dashboard = () => {
  const { currentConversationId, resume, profile, setProfile, setResume } = useStore();
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showResumeUploader, setShowResumeUploader] = useState(false);
  const [profileLoading, setProfileLoading] = useState(true);

  // Load profile data on component mount
  useEffect(() => {
    const loadProfileData = async () => {
      try {
        const response = await axios.get('/api/candidate-data', {
          withCredentials: true,
        });

        const profileData = response.data;
        
        // Store profile data in Zustand
        setProfile(profileData);

        // Check if resume has meaningful content
        const resumeData = profileData?.resume;
        const hasResume = Boolean(
          resumeData && (
            (typeof resumeData.summary === 'string' && resumeData.summary.trim().length > 0) ||
            (Array.isArray(resumeData.experience) && resumeData.experience.length > 0) ||
            (Array.isArray(resumeData.education) && resumeData.education.length > 0) ||
            (Array.isArray(resumeData.skills) && resumeData.skills.length > 0)
          )
        );

        if (hasResume) {
          setResume({ uploaded: true });
          console.log('Existing profile loaded:', profileData);
        } else {
          setResume(null);
        }
      } catch (error) {
        console.error('Error loading profile:', error);
        // Don't show error toast on initial load - user might not have profile yet
      } finally {
        setProfileLoading(false);
      }
    };

    loadProfileData();
  }, [setProfile, setResume]);

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50 dark:bg-gray-950">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="h-16 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {currentConversationId ? 'Content Generator' : 'Dashboard'}
            </h2>
          </div>

          <div className="flex items-center space-x-2">
            {/* Resume upload status */}
            {resume ? (
              <div className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-green-700 dark:text-green-300">
                    Resume Active
                  </span>
                  {resume.processed_at && (
                    <span className="text-[10px] text-green-600 dark:text-green-400">
                      {new Date(resume.processed_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setShowResumeUploader(!showResumeUploader)}
                  className="ml-2 text-xs text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300 underline"
                >
                  Update
                </button>
              </div>
            ) : (
              <motion.button
                onClick={() => setShowResumeUploader(!showResumeUploader)}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Upload className="w-4 h-4" />
                <span className="text-sm font-medium">Upload Resume</span>
              </motion.button>
            )}

            {/* Profile button */}
            <motion.button
              onClick={() => setShowProfileModal(true)}
              className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <User className="w-4 h-4" />
              <span className="text-sm font-medium">Profile</span>
            </motion.button>
          </div>
        </div>

        {/* Resume Uploader Panel */}
        {showResumeUploader && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6"
          >
            <div className="max-w-2xl mx-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Upload Your Resume
                </h3>
                <button
                  onClick={() => setShowResumeUploader(false)}
                  className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  Close
                </button>
              </div>
              <ResumeUploader onUploadComplete={() => setShowResumeUploader(false)} />
            </div>
          </motion.div>
        )}

        {/* Content area */}
        <div className="flex-1 overflow-hidden">
          <ContentGenerator />
        </div>
      </div>

      {/* Profile Modal */}
      <ProfileModal isOpen={showProfileModal} onClose={() => setShowProfileModal(false)} />
    </div>
  );
};

export default Dashboard;
