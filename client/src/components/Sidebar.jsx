import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusCircle,
  MessageSquare,
  FileText,
  Mail,
  User,
  Moon,
  Sun,
  LogOut,
  Menu,
  X,
  Settings,
  Sparkles,
} from 'lucide-react';
import useStore from '../store/useStore';
import { formatDate, getInitials, getColorFromString } from '../utils/helpers';

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(true);

  const {
    user,
    theme,
    toggleTheme,
    logout,
    conversations,
    currentConversationId,
    setCurrentConversation,
    createConversation,
    deleteConversation,
  } = useStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleNewChat = (type) => {
    const titles = {
      cover_letter: 'New Cover Letter',
      email: 'New Email',
      resume: 'Resume Review',
    };
    createConversation(type, titles[type]);
    navigate('/dashboard');
  };

  const conversationTypes = [
    { id: 'cover_letter', label: 'Cover Letter', icon: FileText, color: 'text-blue-600' },
    { id: 'email', label: 'Email', icon: Mail, color: 'text-green-600' },
    { id: 'resume', label: 'Resume', icon: User, color: 'text-purple-600' },
  ];

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-lg"
      >
        {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Backdrop for mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="lg:hidden fixed inset-0 bg-black/50 z-40"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            exit={{ x: -300 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed lg:sticky top-0 left-0 h-screen w-80 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 z-40 flex flex-col"
          >
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-6 h-6 text-blue-600" />
                  <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    Applify
                  </h1>
                </div>
                <button
                  onClick={toggleTheme}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  aria-label="Toggle theme"
                >
                  {theme === 'light' ? (
                    <Moon className="w-5 h-5" />
                  ) : (
                    <Sun className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* New chat buttons */}
              <div className="space-y-2">
                {conversationTypes.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => handleNewChat(type.id)}
                    className="w-full flex items-center space-x-2 px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700 transition-all duration-200 group"
                  >
                    <PlusCircle className="w-4 h-4 group-hover:rotate-90 transition-transform duration-200" />
                    <span className="text-sm font-medium">{type.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Conversations list */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
              <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                Recent Conversations
              </h2>

              {conversations.length === 0 ? (
                <div className="text-center py-8">
                  <MessageSquare className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-700 mb-2" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    No conversations yet
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    Start by creating a new one above
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {conversations.map((conv) => {
                    const typeInfo = conversationTypes.find((t) => t.id === conv.type);
                    const Icon = typeInfo?.icon || MessageSquare;
                    const isActive = conv.id === currentConversationId;

                    return (
                      <motion.button
                        key={conv.id}
                        onClick={() => {
                          setCurrentConversation(conv.id);
                          navigate('/dashboard');
                          setIsOpen(false);
                        }}
                        className={`w-full flex items-start space-x-3 p-3 rounded-lg transition-all duration-200 group ${
                          isActive
                            ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-800 border border-transparent'
                        }`}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <Icon
                          className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                            isActive ? typeInfo?.color : 'text-gray-400'
                          }`}
                        />
                        <div className="flex-1 min-w-0 text-left">
                          <p className="text-sm font-medium truncate text-gray-900 dark:text-gray-100">
                            {conv.title}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {formatDate(conv.updatedAt)}
                          </p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteConversation(conv.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/20 text-red-600 transition-opacity"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </motion.button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* User profile */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-800">
              <div className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer group">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                  style={{ backgroundColor: getColorFromString(user?.email || user?.name || '') }}
                >
                  {getInitials(user?.name || user?.email || 'User')}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate text-gray-900 dark:text-gray-100">
                    {user?.name || 'User'}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {user?.email || ''}
                  </p>
                </div>
                <button
                  onClick={handleLogout}
                  className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/20 text-red-600 transition-opacity"
                  aria-label="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
};

export default Sidebar;
