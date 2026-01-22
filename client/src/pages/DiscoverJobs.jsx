import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  MapPin,
  Building2,
  Briefcase,
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  Loader2,
  Link as LinkIcon,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  X,
} from 'lucide-react';
import Sidebar from '../components/Sidebar';
import JobDetailDrawer from '../components/JobDetailDrawer';
import { jobsAPI } from '../services/api';
import toast from 'react-hot-toast';

const DiscoverJobs = () => {
  // State
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    ats: 'all',
    q: '',
    location: '',
    company: '',
  });
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  });
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [extractUrl, setExtractUrl] = useState('');
  const [extracting, setExtracting] = useState(false);
  
  // Refresh state
  const [refreshState, setRefreshState] = useState({
    status: 'idle', // idle, running, completed, error
    progress: null,
  });
  const [showRefreshPanel, setShowRefreshPanel] = useState(false);
  const streamRef = useRef(null);

  // Fetch jobs
  const fetchJobs = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const response = await jobsAPI.getFeed({
        ...filters,
        page,
        page_size: pagination.pageSize,
      });
      setJobs(response.jobs || []);
      setPagination({
        page: response.page,
        pageSize: response.page_size,
        total: response.total,
        totalPages: response.total_pages,
      });
    } catch (error) {
      toast.error(error.message || 'Failed to load jobs');
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.pageSize]);

  // Initial load
  useEffect(() => {
    fetchJobs();
    checkRefreshStatus();
    
    // Cleanup SSE stream on unmount
    return () => {
      if (streamRef.current) {
        streamRef.current.close();
      }
    };
  }, []);

  // Check if refresh is already running
  const checkRefreshStatus = async () => {
    try {
      const status = await jobsAPI.getRefreshStatus();
      if (status.status === 'running') {
        setRefreshState(status);
        setShowRefreshPanel(true);
        startStreamingProgress();
      }
    } catch (error) {
      // Ignore - might not have any status yet
    }
  };

  // Start refresh
  const handleStartRefresh = async () => {
    try {
      await jobsAPI.startRefresh();
      setRefreshState({ status: 'running', progress: { phase: 'loading', message: 'Starting...' } });
      setShowRefreshPanel(true);
      startStreamingProgress();
    } catch (error) {
      if (error.response?.status === 409) {
        toast.error('Refresh already in progress');
        setShowRefreshPanel(true);
        startStreamingProgress();
      } else {
        toast.error(error.message || 'Failed to start refresh');
      }
    }
  };

  // Start streaming progress updates
  const startStreamingProgress = () => {
    // Close existing stream
    if (streamRef.current) {
      streamRef.current.close();
    }
    
    const stream = jobsAPI.streamRefreshProgress();
    streamRef.current = stream.subscribe(
      (data) => {
        setRefreshState(data);
      },
      (error) => {
        console.error('Stream error:', error);
        setRefreshState({ status: 'error', progress: { message: 'Connection lost' } });
      },
      (data) => {
        // On complete
        if (data.status === 'completed') {
          toast.success(data.progress?.message || 'Jobs refreshed!');
          fetchJobs(); // Reload jobs list
        } else if (data.status === 'error') {
          toast.error(data.progress?.message || 'Refresh failed');
        }
      }
    );
  };

  // Handle filter change with debounce for text fields
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Apply filters
  const applyFilters = () => {
    fetchJobs(1);
  };

  // Handle page change
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      fetchJobs(newPage);
    }
  };

  // Handle job click
  const handleJobClick = (job) => {
    setSelectedJobId(job.id);
    setIsDrawerOpen(true);
  };

  // Handle save job
  const handleSaveJob = async (jobId, e) => {
    e.stopPropagation();
    try {
      await jobsAPI.saveJob(jobId);
      toast.success('Job saved!');
      // Update local state
      setJobs(prev => prev.map(job => 
        job.id === jobId ? { ...job, saved_status: 'saved' } : job
      ));
    } catch (error) {
      toast.error(error.message || 'Failed to save job');
    }
  };

  // Handle URL extraction
  const handleExtract = async (e) => {
    e.preventDefault();
    if (!extractUrl.trim()) {
      toast.error('Please enter a job URL');
      return;
    }

    setExtracting(true);
    try {
      const response = await jobsAPI.extractJob(extractUrl);
      if (response.success && response.job) {
        toast.success(response.message || 'Job extracted!');
        setExtractUrl('');
        // Add to jobs list at the beginning
        setJobs(prev => [response.job, ...prev.filter(j => j.id !== response.job.id)]);
        // Open the drawer for the new job
        setSelectedJobId(response.job.id);
        setIsDrawerOpen(true);
      }
    } catch (error) {
      toast.error(error.message || 'Failed to extract job');
    } finally {
      setExtracting(false);
    }
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
    <div className="h-screen grid lg:grid-cols-[280px_1fr] overflow-hidden bg-gray-50 dark:bg-gray-950">
      <Sidebar />

      <div className="flex flex-col min-h-0 overflow-hidden">
        {/* Top bar */}
        <div className="h-16 flex-shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Discover Jobs
            </h2>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {pagination.total} jobs from top startups
            </span>
          </div>
          <button
            onClick={handleStartRefresh}
            disabled={refreshState.status === 'running'}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              refreshState.status === 'running'
                ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            <RefreshCw className={`w-4 h-4 ${refreshState.status === 'running' ? 'animate-spin' : ''}`} />
            {refreshState.status === 'running' ? 'Refreshing...' : 'Refresh Jobs'}
          </button>
        </div>

        {/* Refresh Progress Panel */}
        <AnimatePresence>
          {showRefreshPanel && refreshState.status !== 'idle' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="border-b border-gray-200 dark:border-gray-800 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/10 dark:to-purple-900/10 overflow-hidden"
            >
              <div className="px-6 py-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {refreshState.status === 'running' && (
                      <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                    )}
                    {refreshState.status === 'completed' && (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    )}
                    {refreshState.status === 'error' && (
                      <AlertCircle className="w-5 h-5 text-red-600" />
                    )}
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {refreshState.progress?.message || 'Processing...'}
                    </span>
                  </div>
                  <button
                    onClick={() => setShowRefreshPanel(false)}
                    className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                  >
                    <X className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
                
                {refreshState.progress && refreshState.progress.total > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span>
                        {refreshState.progress.current || 0} / {refreshState.progress.total} companies
                      </span>
                      <span>
                        {refreshState.progress.jobs_found || 0} jobs found
                        {refreshState.progress.errors > 0 && (
                          <span className="text-amber-600 ml-2">
                            ({refreshState.progress.errors} errors)
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                        initial={{ width: 0 }}
                        animate={{ 
                          width: `${Math.round((refreshState.progress.current / refreshState.progress.total) * 100)}%` 
                        }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-6xl mx-auto">
            {/* Extract Job URL Section */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
            >
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                Have a job URL? Paste it here to extract and save
              </h3>
              <form onSubmit={handleExtract} className="flex gap-3">
                <div className="relative flex-1">
                  <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="url"
                    value={extractUrl}
                    onChange={(e) => setExtractUrl(e.target.value)}
                    placeholder="https://jobs.company.com/position..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={extracting}
                  />
                </div>
                <button
                  type="submit"
                  disabled={extracting}
                  className="px-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {extracting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Extracting...
                    </>
                  ) : (
                    'Extract Job'
                  )}
                </button>
              </form>
            </motion.div>

            {/* Filters */}
            <div className="mb-6 p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <Filter className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filters</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* ATS Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    ATS Platform
                  </label>
                  <select
                    value={filters.ats}
                    onChange={(e) => handleFilterChange('ats', e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm"
                  >
                    <option value="all">All Platforms</option>
                    <option value="greenhouse">Greenhouse</option>
                    <option value="ashby">Ashby</option>
                  </select>
                </div>

                {/* Search Query */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Search
                  </label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={filters.q}
                      onChange={(e) => handleFilterChange('q', e.target.value)}
                      placeholder="Job title..."
                      className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm"
                    />
                  </div>
                </div>

                {/* Company Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Company
                  </label>
                  <div className="relative">
                    <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={filters.company}
                      onChange={(e) => handleFilterChange('company', e.target.value)}
                      placeholder="Company name..."
                      className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm"
                    />
                  </div>
                </div>

                {/* Location Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Location
                  </label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={filters.location}
                      onChange={(e) => handleFilterChange('location', e.target.value)}
                      placeholder="Location..."
                      className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm"
                    />
                  </div>
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  onClick={applyFilters}
                  className="px-4 py-2 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-lg font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Apply Filters
                </button>
              </div>
            </div>

            {/* Jobs List */}
            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              </div>
            ) : jobs.length === 0 ? (
              <div className="text-center py-16">
                <Briefcase className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-700 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                  No jobs found
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  Try adjusting your filters or paste a job URL above
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {jobs.map((job) => (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    onClick={() => handleJobClick(job)}
                    className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg hover:border-blue-300 dark:hover:border-blue-700 cursor-pointer transition-all group"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                            {job.title}
                          </h3>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getAtsBadgeColor(job.ats_type)}`}>
                            {job.ats_type}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                          {job.company_name}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                          {job.location && (
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              {job.location}
                            </span>
                          )}
                          {job.team && (
                            <span className="flex items-center gap-1">
                              <Briefcase className="w-3 h-3" />
                              {job.team}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => handleSaveJob(job.id, e)}
                          className={`p-2 rounded-lg transition-colors ${
                            job.saved_status
                              ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                              : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-blue-600'
                          }`}
                          title={job.saved_status ? 'Saved' : 'Save job'}
                        >
                          {job.saved_status ? (
                            <BookmarkCheck className="w-5 h-5" />
                          ) : (
                            <Bookmark className="w-5 h-5" />
                          )}
                        </button>
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 transition-colors"
                          title="Open original"
                        >
                          <ExternalLink className="w-5 h-5" />
                        </a>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {/* Pagination */}
            {!loading && pagination.totalPages > 1 && (
              <div className="mt-6 flex items-center justify-center gap-2">
                <button
                  onClick={() => handlePageChange(pagination.page - 1)}
                  disabled={pagination.page === 1}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Page {pagination.page} of {pagination.totalPages}
                </span>
                <button
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={pagination.page === pagination.totalPages}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Job Detail Drawer */}
      <JobDetailDrawer
        jobId={selectedJobId}
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedJobId(null);
        }}
        onJobUpdate={(updatedJob) => {
          setJobs(prev => prev.map(job => 
            job.id === updatedJob.id ? { ...job, ...updatedJob } : job
          ));
        }}
      />
    </div>
  );
};

export default DiscoverJobs;
