import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Sparkles,
  Copy,
  Download,
  RefreshCw,
  User,
  Bot,
  Loader2,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import useStore from '../store/useStore';
import { contentAPI } from '../services/api';
import { copyToClipboard, downloadFile, formatTime } from '../utils/helpers';
import toast from 'react-hot-toast';
import ResumeUploader from './ResumeUploader';

const ContentGenerator = () => {
  const {
    currentConversationId,
    conversations,
    addMessage,
    updateMessage,
    isGenerating,
    setGenerating,
    resume,
  } = useStore();

  const [input, setInput] = useState('');
  const [showResumeUploader, setShowResumeUploader] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const currentConversation = conversations.find((c) => c.id === currentConversationId);

  useEffect(() => {
    scrollToBottom();
  }, [currentConversation?.messages]);

  useEffect(() => {
    adjustTextareaHeight();
  }, [input]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  };

  const handleCopy = async (content) => {
    const success = await copyToClipboard(content);
    if (success) {
      toast.success('Copied to clipboard!');
    } else {
      toast.error('Failed to copy');
    }
  };

  const handleDownload = (content, type) => {
    const filename = `${type}_${Date.now()}.txt`;
    downloadFile(content, filename, 'text/plain');
    toast.success('Downloaded successfully!');
  };

  const handleGenerate = async () => {
    if (!input.trim() || isGenerating || !currentConversationId) return;

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    addMessage(currentConversationId, userMessage);
    setInput('');
    setGenerating(true);

    // Add a placeholder AI message
    const aiMessageIndex = currentConversation?.messages.length || 0;
    const aiMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      loading: true,
    };
    addMessage(currentConversationId, aiMessage);

    try {
      let response;
      const conversationType = currentConversation?.type;

      // Determine which API endpoint to use based on conversation type
      switch (conversationType) {
        case 'cover_letter':
          response = await contentAPI.generateCoverLetter(input.trim(), {
            resume: resume?.content,
          });
          break;

        case 'email':
          response = await contentAPI.generateEmail('professional', 'Hiring Manager', input.trim());
          break;

        case 'resume':
          response = await contentAPI.generateResumeTailored(input.trim());
          break;

        default:
          response = await contentAPI.generate(conversationType, {
            prompt: input.trim(),
            resume: resume?.content,
          });
      }

      // Update the AI message with the response
      updateMessage(currentConversationId, aiMessageIndex + 1, {
        content: response.content || response.text || response.result || 'No response generated',
        loading: false,
      });
    } catch (error) {
      updateMessage(currentConversationId, aiMessageIndex + 1, {
        content: `Error: ${error.message || 'Failed to generate content'}`,
        loading: false,
        error: true,
      });
      toast.error(error.message || 'Failed to generate content');
    } finally {
      setGenerating(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  const handleRegenerate = async (messageIndex) => {
    if (messageIndex < 1) return;

    const previousUserMessage = currentConversation?.messages[messageIndex - 1];
    if (!previousUserMessage || previousUserMessage.role !== 'user') return;

    setGenerating(true);
    updateMessage(currentConversationId, messageIndex, {
      loading: true,
      content: '',
    });

    try {
      let response;
      const conversationType = currentConversation?.type;

      switch (conversationType) {
        case 'cover_letter':
          response = await contentAPI.generateCoverLetter(previousUserMessage.content, {
            resume: resume?.content,
          });
          break;

        case 'email':
          response = await contentAPI.generateEmail('professional', 'Hiring Manager', previousUserMessage.content);
          break;

        case 'resume':
          response = await contentAPI.generateResumeTailored(previousUserMessage.content);
          break;

        default:
          response = await contentAPI.generate(conversationType, {
            prompt: previousUserMessage.content,
            resume: resume?.content,
          });
      }

      updateMessage(currentConversationId, messageIndex, {
        content: response.content || response.text || response.result || 'No response generated',
        loading: false,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      updateMessage(currentConversationId, messageIndex, {
        content: `Error: ${error.message || 'Failed to regenerate content'}`,
        loading: false,
        error: true,
      });
      toast.error(error.message || 'Failed to regenerate content');
    } finally {
      setGenerating(false);
    }
  };

  if (!currentConversationId) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Sparkles className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-700 mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            No conversation selected
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            Select a conversation from the sidebar or create a new one
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 md:p-6 space-y-6">
        {currentConversation?.messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <Sparkles className="w-16 h-16 mx-auto text-blue-500 mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Ready to help you craft the perfect content
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                {currentConversation?.type === 'cover_letter' &&
                  'Paste a job description to generate a tailored cover letter'}
                {currentConversation?.type === 'email' &&
                  'Describe the email you need and I\'ll help you write it'}
                {currentConversation?.type === 'resume' &&
                  'Paste a job description to tailor your resume'}
              </p>

              {!resume && (
                <button
                  onClick={() => setShowResumeUploader(!showResumeUploader)}
                  className="btn btn-outline mx-auto"
                >
                  {showResumeUploader ? 'Hide Resume Uploader' : 'Upload Resume First'}
                </button>
              )}

              {showResumeUploader && (
                <div className="mt-6">
                  <ResumeUploader onUploadComplete={() => setShowResumeUploader(false)} />
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            {currentConversation?.messages.map((message, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`flex space-x-3 max-w-[85%] ${
                    message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gradient-to-br from-purple-600 to-blue-600 text-white'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <User className="w-5 h-5" />
                    ) : (
                      <Bot className="w-5 h-5" />
                    )}
                  </div>

                  {/* Message content */}
                  <div className="flex-1 min-w-0">
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : message.error
                          ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-900 dark:text-red-100'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                      }`}
                    >
                      {message.loading ? (
                        <div className="flex items-center space-x-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span className="text-sm">Generating...</span>
                        </div>
                      ) : (
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                      )}
                    </div>

                    {/* Message actions */}
                    {message.role === 'assistant' && !message.loading && (
                      <div className="flex items-center space-x-2 mt-2 ml-2">
                        <span className="text-xs text-gray-400">
                          {formatTime(message.timestamp)}
                        </span>
                        <button
                          onClick={() => handleCopy(message.content)}
                          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                          title="Copy"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDownload(message.content, currentConversation?.type)}
                          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                          title="Download"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleRegenerate(index)}
                          disabled={isGenerating}
                          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors disabled:opacity-50"
                          title="Regenerate"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 dark:border-gray-800 p-4 bg-white dark:bg-gray-900">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end space-x-3">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  currentConversation?.type === 'cover_letter'
                    ? 'Paste the job description here...'
                    : currentConversation?.type === 'email'
                    ? 'Describe the email you need...'
                    : 'Paste the job description to tailor your resume...'
                }
                className="w-full resize-none rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows="1"
                disabled={isGenerating}
              />
            </div>

            <motion.button
              onClick={handleGenerate}
              disabled={!input.trim() || isGenerating}
              className="p-3 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:from-blue-700 hover:to-purple-700 transition-all"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {isGenerating ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </motion.button>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
            Press Enter to send, Shift + Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
};

export default ContentGenerator;
