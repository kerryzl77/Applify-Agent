import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  MapPin,
  Building2,
  Briefcase,
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  Loader2,
  Rocket,
  Clock,
  FileText,
} from 'lucide-react';
import { jobsAPI } from '../services/api';
import toast from 'react-hot-toast';

const JobDetailDrawer = ({ jobId, isOpen, onClose, onJobUpdate }) => {
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [startingCampaign, setStartingCampaign] = useState(false);

  useEffect(() => {
    if (isOpen && jobId) {
      fetchJobDetails();
    }
  }, [isOpen, jobId]);

  const fetchJobDetails = async () => {
    setLoading(true);
    try {
      const response = await jobsAPI.getJob(jobId, true); // include JD
      setJob(response);
    } catch (error) {
      toast.error(error.message || 'Failed to load job details');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!job) return;
    setSaving(true);
    try {
      await jobsAPI.saveJob(job.id);
      toast.success('Job saved!');
      const updatedJob = { ...job, saved_status: 'saved' };
      setJob(updatedJob);
      onJobUpdate?.(updatedJob);
    } catch (error) {
      toast.error(error.message || 'Failed to save job');
    } finally {
      setSaving(false);
    }
  };

  const handleStartCampaign = async () => {
    if (!job) return;
    setStartingCampaign(true);
    try {
      const response = await jobsAPI.startCampaign(job.id);
      toast.success(response.message || 'Campaign started!');
      const updatedJob = { ...job, saved_status: 'campaign_started' };
      setJob(updatedJob);
      onJobUpdate?.(updatedJob);
      
      // Navigate to campaign page
      if (response.campaign_id) {
        onClose();
        navigate(`/campaigns/${response.campaign_id}`);
      }
    } catch (error) {
      toast.error(error.message || 'Failed to start campaign');
    } finally {
      setStartingCampaign(false);
    }
  };

  // Get status badge
  const getStatusBadge = () => {
    if (!job?.saved_status) return null;
    
    const badges = {
      saved: {
        color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
        icon: BookmarkCheck,
        label: 'Saved',
      },
      campaign_started: {
        color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
        icon: Rocket,
        label: 'Campaign Started',
      },
      archived: {
        color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
        icon: Clock,
        label: 'Archived',
      },
    };
    
    const badge = badges[job.saved_status];
    if (!badge) return null;
    
    const Icon = badge.icon;
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        <Icon className="w-3 h-3" />
        {badge.label}
      </span>
    );
  };

  // Get ATS badge color
  const getAtsBadgeColor = (atsType) => {
    switch (atsType) {
      case 'greenhouse':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'ashby':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40"
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-screen w-full max-w-lg bg-white dark:bg-gray-900 shadow-xl z-50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0 pr-4">
                  {loading ? (
                    <div className="animate-pulse">
                      <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2" />
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                    </div>
                  ) : job ? (
                    <>
                      <div className="flex items-center gap-2 mb-1">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
                          {job.title}
                        </h2>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getAtsBadgeColor(job.ats_type)}`}>
                          {job.ats_type}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {job.company_name}
                      </p>
                      {getStatusBadge() && (
                        <div className="mt-2">
                          {getStatusBadge()}
                        </div>
                      )}
                    </>
                  ) : null}
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                </div>
              ) : job ? (
                <div className="space-y-6">
                  {/* Meta info */}
                  <div className="grid grid-cols-2 gap-4">
                    {job.location && (
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <MapPin className="w-4 h-4 text-gray-400" />
                        <span>{job.location}</span>
                      </div>
                    )}
                    {job.team && (
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <Building2 className="w-4 h-4 text-gray-400" />
                        <span>{job.team}</span>
                      </div>
                    )}
                    {job.employment_type && (
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <Briefcase className="w-4 h-4 text-gray-400" />
                        <span>{job.employment_type}</span>
                      </div>
                    )}
                  </div>

                  {/* Job Description */}
                  {job.job_description ? (
                    <div>
                      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                        <FileText className="w-4 h-4" />
                        Job Description
                      </h3>
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <div 
                          className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap"
                          dangerouslySetInnerHTML={{ __html: job.job_description.replace(/\n/g, '<br />') }}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                      <FileText className="w-8 h-8 mx-auto text-gray-300 dark:text-gray-600 mb-2" />
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Job description is loading or not available.
                      </p>
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 mt-2 hover:underline"
                      >
                        View original posting
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}

                  {/* Requirements */}
                  {job.requirements && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                        Requirements
                      </h3>
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <div 
                          className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap"
                          dangerouslySetInnerHTML={{ __html: job.requirements.replace(/\n/g, '<br />') }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* Footer Actions */}
            {job && !loading && (
              <div className="flex-shrink-0 p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
                <div className="flex items-center gap-3">
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    View Original
                  </a>
                  
                  {!job.saved_status && (
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
                    >
                      {saving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Bookmark className="w-4 h-4" />
                      )}
                      Save
                    </button>
                  )}
                  
                  {job.saved_status !== 'campaign_started' && (
                    <button
                      onClick={handleStartCampaign}
                      disabled={startingCampaign}
                      className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                    >
                      {startingCampaign ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Rocket className="w-4 h-4" />
                      )}
                      Start Campaign
                    </button>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default JobDetailDrawer;
