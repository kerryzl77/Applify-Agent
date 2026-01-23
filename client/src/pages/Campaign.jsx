import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  FileText,
  Mail,
  Calendar,
  CheckCircle,
  Circle,
  Loader2,
  AlertCircle,
  Users,
  Lightbulb,
  Send,
  MessageSquare,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ArrowLeft,
  Play,
  Check,
  Clock,
} from 'lucide-react';
import Sidebar from '../components/Sidebar';
import GmailSetup from '../components/GmailSetup';
import { campaignAPI, gmailAPI } from '../services/api';
import toast from 'react-hot-toast';

// Step status icons
const StepIcon = ({ status }) => {
  switch (status) {
    case 'done':
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    case 'running':
      return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
    case 'error':
      return <AlertCircle className="w-5 h-5 text-red-500" />;
    case 'waiting_user':
      return <Clock className="w-5 h-5 text-amber-500" />;
    default:
      return <Circle className="w-5 h-5 text-gray-300" />;
  }
};

// Step card component
const StepCard = ({ step, name, icon: Icon, status, isActive, trace }) => {
  const [expanded, setExpanded] = useState(false);
  
  const stepTrace = trace?.filter(t => t.step === step) || [];
  
  return (
    <div
      className={`p-4 rounded-lg border transition-all ${
        isActive
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : status === 'done'
          ? 'border-green-200 bg-green-50 dark:bg-green-900/10'
          : status === 'error'
          ? 'border-red-200 bg-red-50 dark:bg-red-900/10'
          : 'border-gray-200 dark:border-gray-700'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${
            isActive ? 'bg-blue-100 dark:bg-blue-800' : 'bg-gray-100 dark:bg-gray-800'
          }`}>
            <Icon className={`w-5 h-5 ${
              isActive ? 'text-blue-600' : 'text-gray-500'
            }`} />
          </div>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">{name}</h3>
            <p className="text-sm text-gray-500 capitalize">{status || 'queued'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StepIcon status={status} />
          {stepTrace.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>
      
      <AnimatePresence>
        {expanded && stepTrace.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700"
          >
            <div className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
              {stepTrace.slice(-5).map((t, i) => (
                <p key={i}>{t.message || t.summary || t.type}</p>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Contact card for selection
const ContactCard = ({ contact, selected, onSelect, role }) => (
  <div
    onClick={() => onSelect(contact, role)}
    className={`p-3 rounded-lg border cursor-pointer transition-all ${
      selected
        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
        : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
    }`}
  >
    <div className="flex items-start justify-between">
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
          {contact.name}
        </h4>
        <p className="text-sm text-gray-500 truncate">{contact.title}</p>
        <p className="text-xs text-gray-400 mt-1">{contact.reason}</p>
      </div>
      <div className="flex flex-col items-end gap-1">
        {selected && <Check className="w-5 h-5 text-blue-500" />}
        <div className="flex gap-1">
          {contact.tags?.slice(0, 2).map((tag, i) => (
            <span
              key={i}
              className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
    {contact.source_url && (
      <a
        href={contact.source_url}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className="inline-flex items-center gap-1 text-xs text-blue-500 mt-2 hover:underline"
      >
        <ExternalLink className="w-3 h-3" />
        Source
      </a>
    )}
  </div>
);

// Draft panel component
const DraftPanel = ({ drafts, onRegenerate, onFeedback }) => {
  const [activeDraft, setActiveDraft] = useState('recruiter_email');
  const [feedbackText, setFeedbackText] = useState('');
  
  const draftTypes = [
    { key: 'warm_intro', label: 'Warm Intro', icon: MessageSquare },
    { key: 'recruiter_email', label: 'Recruiter', icon: Mail },
    { key: 'hm_email', label: 'Hiring Manager', icon: Mail },
    { key: 'linkedin_note', label: 'LinkedIn', icon: Users },
  ];
  
  const currentDraft = drafts?.[activeDraft];
  
  const handleFeedback = () => {
    if (feedbackText.trim()) {
      onFeedback(activeDraft, feedbackText);
      setFeedbackText('');
    }
  };
  
  return (
    <div className="space-y-4">
      {/* Draft type tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {draftTypes.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveDraft(key)}
            disabled={!drafts?.[key]}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg whitespace-nowrap transition-all ${
              activeDraft === key
                ? 'bg-blue-600 text-white'
                : drafts?.[key]
                ? 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
                : 'bg-gray-50 dark:bg-gray-900 text-gray-400 cursor-not-allowed'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>
      
      {/* Draft content */}
      {currentDraft ? (
        <div className="space-y-4">
          {currentDraft.subject && (
            <div>
              <label className="text-sm font-medium text-gray-500">Subject</label>
              <p className="mt-1 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-gray-900 dark:text-gray-100">
                {currentDraft.subject}
              </p>
            </div>
          )}
          <div>
            <label className="text-sm font-medium text-gray-500">Body</label>
            <div className="mt-1 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg whitespace-pre-wrap text-gray-900 dark:text-gray-100">
              {currentDraft.body}
            </div>
          </div>
          
          {/* Feedback input */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-500">Feedback (optional)</label>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="e.g., Make it more concise, add more technical details..."
              className="w-full p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 resize-none"
              rows={2}
            />
            <div className="flex gap-2">
              <button
                onClick={handleFeedback}
                disabled={!feedbackText.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-lg font-medium hover:opacity-90 disabled:opacity-50"
              >
                <RefreshCw className="w-4 h-4" />
                Regenerate with Feedback
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-2 text-gray-300" />
          <p>No draft available yet</p>
        </div>
      )}
    </div>
  );
};

// Main Campaign page
const Campaign = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const streamRef = useRef(null);
  const traceIndexRef = useRef(0);
  const fetchIdRef = useRef(0);
  
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [selectedContacts, setSelectedContacts] = useState({});
  const [activePanel, setActivePanel] = useState('contacts');
  const [trace, setTrace] = useState([]);
  const [gmailStatus, setGmailStatus] = useState({ availability: 'unknown', authorized: false });
  const [isGmailSetupOpen, setGmailSetupOpen] = useState(false);
  
  // Fetch campaign data
  const fetchCampaign = useCallback(async () => {
    const requestId = ++fetchIdRef.current;
    try {
      const data = await campaignAPI.get(campaignId);
      if (requestId !== fetchIdRef.current) {
        return;
      }
      const serverTrace = data.state?.trace || [];
      setCampaign(data);
      setTrace(serverTrace);
      traceIndexRef.current = serverTrace.length;
      
      // Initialize selected contacts from state
      if (data.state?.selected_contacts) {
        setSelectedContacts(data.state.selected_contacts);
      }
    } catch (error) {
      if (requestId === fetchIdRef.current) {
        toast.error(error.message || 'Failed to load campaign');
      }
    } finally {
      if (requestId === fetchIdRef.current) {
        setLoading(false);
      }
    }
  }, [campaignId]);
  
  useEffect(() => {
    fetchCampaign();
    
    return () => {
      if (streamRef.current) {
        streamRef.current.close();
      }
    };
  }, [fetchCampaign]);

  const refreshGmailStatus = useCallback(async () => {
    try {
      const status = await gmailAPI.status();
      setGmailStatus(status);
      return status;
    } catch (error) {
      const fallback = { availability: 'unavailable', authorized: false, error: error.message };
      setGmailStatus(fallback);
      return fallback;
    }
  }, []);

  useEffect(() => {
    refreshGmailStatus();
  }, [refreshGmailStatus]);

  // If backend pauses for user input, allow UI actions immediately.
  useEffect(() => {
    const currentPhase = campaign?.state?.phase;
    if (currentPhase === 'waiting_user' || currentPhase === 'done' || currentPhase === 'error') {
      setRunning(false);
    }
  }, [campaign?.state?.phase]);

  const applyEventToCampaign = useCallback((event) => {
    if (!event?.type) {
      return;
    }

    setCampaign((prev) => {
      if (!prev) {
        return prev;
      }

      const prevState = prev.state || {};
      const nextState = { ...prevState };
      const steps = { ...(prevState.steps || {}) };
      const artifacts = { ...(prevState.artifacts || {}) };
      let phase = prevState.phase;

      switch (event.type) {
        case 'workflow_start':
          phase = 'running';
          break;
        case 'step_start':
          if (event.step) {
            steps[event.step] = { ...(steps[event.step] || {}), status: 'running' };
          }
          phase = phase === 'idle' ? 'running' : phase;
          break;
        case 'step_done':
          if (event.step) {
            steps[event.step] = { ...(steps[event.step] || {}), status: 'done' };
            if (event.step === 'drafts') {
              steps.schedule = { ...(steps.schedule || {}), status: 'done' };
            }
          }
          break;
        case 'step_error':
          if (event.step) {
            steps[event.step] = { ...(steps[event.step] || {}), status: 'error' };
          }
          phase = 'error';
          break;
        case 'artifact':
          if (event.artifact_type && event.data !== undefined) {
            artifacts[event.artifact_type] = event.data;
          }
          break;
        case 'waiting_user':
          phase = 'waiting_user';
          break;
        case 'workflow_complete':
          phase = phase === 'running' ? 'waiting_user' : phase;
          break;
        case 'error':
          phase = 'error';
          break;
        default:
          break;
      }

      nextState.steps = steps;
      nextState.artifacts = artifacts;
      if (phase) {
        nextState.phase = phase;
      }

      return { ...prev, state: nextState };
    });
  }, []);
  
  // Start workflow
  const handleRun = async (mode = 'full') => {
    setRunning(true);
    setTrace([]);
    traceIndexRef.current = 0;
    
    try {
      await campaignAPI.run(campaignId, { mode });
      startStreaming();
    } catch (error) {
      toast.error(error.message || 'Failed to start workflow');
      setRunning(false);
    }
  };
  
  // Start SSE streaming
  const startStreaming = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.close();
    }

    const fromIndex = traceIndexRef.current;
    const stream = campaignAPI.streamEvents(campaignId, { fromIndex });
    streamRef.current = stream.subscribe(
      (event) => {
        const isTraceEvent = !!event?.timestamp;
        if (isTraceEvent) {
          traceIndexRef.current += 1;
          setTrace((prev) => [...prev, event]);
        }

        applyEventToCampaign(event);
        if (event.type === 'workflow_start' || event.type === 'step_start') {
          setRunning(true);
        }
        
        // Backend can pause at waiting_user without closing SSE; allow UI actions.
        if (event.type === 'waiting_user') {
          fetchCampaign();
          setRunning(false);
          streamRef.current?.close?.();
          streamRef.current = null;
        }

        if (event.type === 'error' || event.type === 'step_error') {
          fetchCampaign();
        }
      },
      (error) => {
        console.error('Stream error:', error);
        setRunning(false);
        streamRef.current = null;
      },
      (data) => {
        setRunning(false);
        fetchCampaign();
        streamRef.current = null;
        
        if (data.type === 'workflow_complete') {
          toast.success('Workflow completed!');
        } else if (data.type === 'error') {
          toast.error(data.message || 'Workflow failed');
        }
      }
    );
  }, [applyEventToCampaign, campaignId, fetchCampaign]);

  useEffect(() => {
    const steps = campaign?.state?.steps || {};
    const hasRunningStep = Object.values(steps).some((step) => step?.status === 'running');
    if (hasRunningStep && !streamRef.current) {
      startStreaming();
    }
  }, [campaign?.state?.steps, startStreaming]);
  
  // Handle contact selection
  const handleSelectContact = (contact, role) => {
    setSelectedContacts((prev) => {
      const current = prev[role];
      if (current?.name === contact.name) {
        // Deselect
        const { [role]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [role]: contact };
    });
  };
  
  // Confirm contact selection
  const handleConfirmContacts = async () => {
    if (Object.keys(selectedContacts).length === 0) {
      toast.error('Please select at least one contact');
      return;
    }
    
    try {
      await campaignAPI.confirm(campaignId, { selected_contacts: selectedContacts });
      toast.success('Contacts confirmed! Generating drafts...');
      handleRun('draft_only');
    } catch (error) {
      toast.error(error.message || 'Failed to confirm contacts');
    }
  };
  
  // Handle feedback and regenerate
  const handleFeedback = async (scope, text) => {
    try {
      await campaignAPI.feedback(campaignId, { scope, text, must: true });
      toast.success('Feedback added, regenerating...');
      handleRun('draft_only');
    } catch (error) {
      toast.error(error.message || 'Failed to add feedback');
    }
  };
  
  // Create Gmail drafts
  const handleCreateGmailDrafts = async () => {
    try {
      const result = await campaignAPI.confirm(campaignId, {
        create_gmail_drafts: true,
        schedule_followups: true,
      });
      
      if (result.gmail_drafts_created > 0) {
        toast.success(`Created ${result.gmail_drafts_created} Gmail drafts!`);
      } else {
        toast.error('No drafts were created');
      }
      
      fetchCampaign();
    } catch (error) {
      toast.error(error.message || 'Failed to create Gmail drafts');
    }
  };

  const handleConnectGmail = async () => {
    try {
      const { auth_url } = await gmailAPI.getAuthUrl();
      window.location.href = auth_url;
    } catch (error) {
      toast.error(error.message || 'Failed to initiate Gmail authorization');
    }
  };

  const handleDisconnectGmail = async () => {
    try {
      await gmailAPI.disconnect();
      toast.success('Gmail disconnected');
      refreshGmailStatus();
    } catch (error) {
      toast.error(error.message || 'Failed to disconnect Gmail');
    }
  };

  const handleGmailAction = async () => {
    const status = await refreshGmailStatus();

    if (status?.availability === 'unavailable') {
      toast.error('Gmail API is not configured');
      setGmailSetupOpen(true);
      return;
    }

    if (!status?.authorized) {
      toast.error('Connect your Gmail account first');
      setGmailSetupOpen(true);
      return;
    }

    await handleCreateGmailDrafts();
  };
  
  if (loading) {
    return (
      <div className="h-screen grid lg:grid-cols-[280px_1fr] overflow-hidden bg-gray-50 dark:bg-gray-950">
        <Sidebar />
        <div className="flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }
  
  if (!campaign) {
    return (
      <div className="h-screen grid lg:grid-cols-[280px_1fr] overflow-hidden bg-gray-50 dark:bg-gray-950">
        <Sidebar />
        <div className="flex flex-col items-center justify-center">
          <AlertCircle className="w-12 h-12 text-gray-400 mb-4" />
          <p className="text-gray-500">Campaign not found</p>
          <button
            onClick={() => navigate('/discover')}
            className="mt-4 text-blue-600 hover:underline"
          >
            Back to Discover Jobs
          </button>
        </div>
      </div>
    );
  }
  
  const state = campaign.state || {};
  const steps = state.steps || {};
  const artifacts = state.artifacts || {};
  const phase = state.phase || 'idle';
  const gmailActionLabel = gmailStatus?.authorized
    ? 'Create Gmail Drafts'
    : gmailStatus?.availability === 'unavailable'
    ? 'Configure Gmail'
    : 'Connect Gmail';
  
  const stepConfig = [
    { step: 'research', name: 'Research Contacts', icon: Search },
    { step: 'evidence', name: 'Build Evidence', icon: Lightbulb },
    { step: 'drafts', name: 'Generate Drafts', icon: FileText },
    { step: 'schedule', name: 'Schedule Follow-ups', icon: Calendar },
    { step: 'gmail', name: 'Create Drafts', icon: Send },
  ];
  
  return (
    <>
      <div className="h-screen grid lg:grid-cols-[280px_1fr] overflow-hidden bg-gray-50 dark:bg-gray-950">
        <Sidebar />
        
        <div className="flex flex-col min-h-0 overflow-hidden">
          {/* Header */}
          <div className="h-16 flex-shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between px-6">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/discover')}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Campaign: {campaign.job?.title}
                </h2>
                <p className="text-sm text-gray-500">
                  {campaign.job?.company_name} - {campaign.job?.location}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {phase === 'idle' && (
                <button
                  onClick={() => handleRun('full')}
                  disabled={running}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {running ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Start Campaign
                </button>
              )}
              
              {phase === 'waiting_user' && !artifacts.drafts && (
                <button
                  onClick={handleConfirmContacts}
                  disabled={running || Object.keys(selectedContacts).length === 0}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  <Check className="w-4 h-4" />
                  Confirm & Generate Drafts
                </button>
              )}
              
              {artifacts.drafts && phase !== 'done' && (
                <button
                  onClick={handleGmailAction}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:opacity-90"
                >
                  <Send className="w-4 h-4" />
                  {gmailActionLabel}
                </button>
              )}
              
              {phase === 'done' && (
                <span className="flex items-center gap-2 px-4 py-2 bg-green-100 text-green-700 rounded-lg font-medium">
                  <CheckCircle className="w-4 h-4" />
                  Campaign Complete
                </span>
              )}
            </div>
          </div>
          
          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-6xl mx-auto space-y-6">
              {/* Step Map */}
              <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
                <h3 className="text-sm font-semibold text-gray-500 uppercase mb-4">Workflow Progress</h3>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  {stepConfig.map(({ step, name, icon }) => (
                    <StepCard
                      key={step}
                      step={step}
                      name={name}
                      icon={icon}
                      status={steps[step]?.status}
                      isActive={steps[step]?.status === 'running'}
                      trace={trace}
                    />
                  ))}
                </div>
              </div>
              
              {/* Panel tabs */}
              <div className="flex gap-2 overflow-x-auto">
                {[
                  { key: 'contacts', label: 'Contacts', icon: Users, count: artifacts.contacts?.length },
                  { key: 'evidence', label: 'Evidence', icon: Lightbulb, count: artifacts.evidence_pack?.why_me_bullets?.length },
                  { key: 'drafts', label: 'Drafts', icon: FileText, count: artifacts.drafts ? Object.keys(artifacts.drafts).length : 0 },
                  { key: 'followups', label: 'Follow-ups', icon: Calendar, count: artifacts.followups?.length },
                ].map(({ key, label, icon: Icon, count }) => (
                  <button
                    key={key}
                    onClick={() => setActivePanel(key)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-all ${
                      activePanel === key
                        ? 'bg-blue-600 text-white'
                        : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-blue-300'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                    {count > 0 && (
                      <span className={`px-1.5 py-0.5 text-xs rounded-full ${
                        activePanel === key
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-600'
                      }`}>
                        {count}
                      </span>
                    )}
                  </button>
                ))}
              </div>
              
              {/* Active Panel Content */}
              <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
                {activePanel === 'contacts' && (
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">Discovered Contacts</h3>
                      {artifacts.contacts?.length > 0 && (
                        <p className="text-sm text-gray-500">
                          Select contacts for outreach (recruiter, hiring manager, warm intro)
                        </p>
                      )}
                    </div>
                    
                    {artifacts.contacts?.length > 0 ? (
                      <div className="space-y-4">
                        {/* Role selection hints */}
                        <div className="flex gap-4 flex-wrap">
                          {['recruiter', 'hiring_manager', 'warm_intro'].map((role) => (
                            <div key={role} className="flex items-center gap-2">
                              <span className={`w-3 h-3 rounded-full ${
                                selectedContacts[role] ? 'bg-blue-500' : 'bg-gray-300'
                              }`} />
                              <span className="text-sm capitalize text-gray-600">
                                {role.replace('_', ' ')}: {selectedContacts[role]?.name || 'Not selected'}
                              </span>
                            </div>
                          ))}
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {artifacts.contacts.map((contact, i) => {
                            const isSelectedAs = Object.entries(selectedContacts).find(
                              ([_, c]) => c?.name === contact.name
                            );
                            return (
                              <div key={i} className="space-y-2">
                                <ContactCard
                                  contact={contact}
                                  selected={!!isSelectedAs}
                                  role={isSelectedAs?.[0]}
                                  onSelect={(c) => {
                                    // Cycle through roles or deselect
                                    const roles = ['recruiter', 'hiring_manager', 'warm_intro'];
                                    const currentRole = isSelectedAs?.[0];
                                    const currentIndex = roles.indexOf(currentRole);
                                    const nextRole = currentIndex === -1 ? roles[0] : 
                                      currentIndex === roles.length - 1 ? null : roles[currentIndex + 1];
                                    
                                    if (nextRole) {
                                      handleSelectContact(c, nextRole);
                                    } else if (currentRole) {
                                      handleSelectContact(c, currentRole); // Deselect
                                    }
                                  }}
                                />
                                {isSelectedAs && (
                                  <p className="text-xs text-center text-blue-600 font-medium capitalize">
                                    Selected as: {isSelectedAs[0].replace('_', ' ')}
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-12">
                        <Users className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-700 mb-4" />
                        <p className="text-gray-500">No contacts discovered yet</p>
                        <p className="text-sm text-gray-400 mt-1">Start the campaign to research contacts</p>
                      </div>
                    )}
                  </div>
                )}
              
              {activePanel === 'evidence' && (
                <div className="space-y-6">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">Evidence Pack</h3>
                  
                  {artifacts.evidence_pack ? (
                    <div className="space-y-6">
                      {/* Why Me Bullets */}
                      <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-3">Why Me Bullets</h4>
                        <div className="space-y-3">
                          {artifacts.evidence_pack.why_me_bullets?.map((bullet, i) => (
                            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                              <p className="text-gray-900 dark:text-gray-100">{bullet.text}</p>
                              {bullet.citations?.length > 0 && (
                                <div className="flex gap-2 mt-2 flex-wrap">
                                  {bullet.citations.map((cite, j) => (
                                    <span
                                      key={j}
                                      className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded"
                                    >
                                      {cite}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      {/* Project Angles */}
                      <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-3">Project Angles</h4>
                        <div className="space-y-3">
                          {artifacts.evidence_pack.project_angles?.map((angle, i) => (
                            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                              <p className="text-gray-900 dark:text-gray-100">{angle.text}</p>
                              {angle.citations?.length > 0 && (
                                <div className="flex gap-2 mt-2 flex-wrap">
                                  {angle.citations.map((cite, j) => (
                                    <span
                                      key={j}
                                      className="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded"
                                    >
                                      {cite}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <Lightbulb className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-700 mb-4" />
                      <p className="text-gray-500">No evidence pack generated yet</p>
                    </div>
                  )}
                </div>
              )}
              
              {activePanel === 'drafts' && (
                <DraftPanel
                  drafts={artifacts.drafts}
                  onFeedback={handleFeedback}
                />
              )}
              
              {activePanel === 'followups' && (
                <div className="space-y-4">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">Follow-up Queue</h3>
                  
                  {artifacts.followups?.length > 0 ? (
                    <div className="space-y-3">
                      {artifacts.followups.map((followup, i) => (
                        <div
                          key={i}
                          className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg flex items-start justify-between"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                                followup.status === 'pending'
                                  ? 'bg-amber-100 text-amber-700'
                                  : followup.status === 'sent'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-gray-100 text-gray-600'
                              }`}>
                                Day {followup.day}
                              </span>
                              <span className="text-sm text-gray-500 capitalize">
                                {followup.draft_type?.replace('_', ' ')}
                              </span>
                            </div>
                            <p className="font-medium text-gray-900 dark:text-gray-100">
                              {followup.subject}
                            </p>
                            <p className="text-sm text-gray-500 mt-1">
                              Due: {new Date(followup.due_at).toLocaleDateString()}
                            </p>
                          </div>
                          <span className={`text-xs px-2 py-1 rounded capitalize ${
                            followup.status === 'pending'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-gray-100 text-gray-600'
                          }`}>
                            {followup.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <Calendar className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-700 mb-4" />
                      <p className="text-gray-500">No follow-ups scheduled yet</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>

    <GmailSetup
      open={isGmailSetupOpen}
      onClose={() => setGmailSetupOpen(false)}
      onConnected={refreshGmailStatus}
      gmailStatus={gmailStatus}
      onConnect={handleConnectGmail}
      onDisconnect={handleDisconnectGmail}
    />
  </>
  );
};

export default Campaign;
