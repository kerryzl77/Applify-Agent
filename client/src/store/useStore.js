import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const useStore = create(
  persist(
    (set, get) => ({
      // User authentication state
      user: null,
      token: null,
      isAuthenticated: false,

      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => set({ token }),

      login: (user, token) => set({
        user,
        token,
        isAuthenticated: true
      }),

      logout: () => set({
        user: null,
        token: null,
        isAuthenticated: false,
        profile: null
      }),

      // Theme state
      theme: 'light',

      setTheme: (theme) => {
        set({ theme });
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      },

      toggleTheme: () => {
        const newTheme = get().theme === 'light' ? 'dark' : 'light';
        get().setTheme(newTheme);
      },

      // Content generation state
      conversations: [],
      currentConversationId: null,
      isGenerating: false,

      createConversation: (type, title = 'New Conversation') => {
        const newConversation = {
          id: Date.now().toString(),
          type, // 'cover_letter', 'email', 'resume'
          title,
          messages: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        set(state => ({
          conversations: [newConversation, ...state.conversations],
          currentConversationId: newConversation.id
        }));

        return newConversation.id;
      },

      setCurrentConversation: (id) => set({ currentConversationId: id }),

      addMessage: (conversationId, message) => {
        set(state => ({
          conversations: state.conversations.map(conv =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, message],
                  updatedAt: new Date().toISOString()
                }
              : conv
          )
        }));
      },

      updateMessage: (conversationId, messageIndex, updates) => {
        set(state => ({
          conversations: state.conversations.map(conv =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: conv.messages.map((msg, idx) =>
                    idx === messageIndex ? { ...msg, ...updates } : msg
                  ),
                  updatedAt: new Date().toISOString()
                }
              : conv
          )
        }));
      },

      deleteConversation: (conversationId) => {
        set(state => {
          const newConversations = state.conversations.filter(c => c.id !== conversationId);
          return {
            conversations: newConversations,
            currentConversationId: state.currentConversationId === conversationId
              ? (newConversations[0]?.id || null)
              : state.currentConversationId
          };
        });
      },

      renameConversation: (conversationId, title) => {
        set(state => ({
          conversations: state.conversations.map(conv =>
            conv.id === conversationId
              ? { ...conv, title, updatedAt: new Date().toISOString() }
              : conv
          )
        }));
      },

      setGenerating: (isGenerating) => set({ isGenerating }),

      // Profile data state
      profile: null,
      profileLoading: false,

      setProfile: (profile) => set({ profile }),
      setProfileLoading: (loading) => set({ profileLoading: loading }),

      updateProfile: (updates) => set(state => ({
        profile: state.profile ? { ...state.profile, ...updates } : updates
      })),

      // Resume state
      resume: null,
      resumeUploading: false,

      setResume: (resume) => set({ resume }),
      setResumeUploading: (uploading) => set({ resumeUploading: uploading }),
    }),
    {
      name: 'applify-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
        theme: state.theme,
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
        profile: state.profile,
        resume: state.resume,
      }),
    }
  )
);

// Initialize theme on load
if (typeof window !== 'undefined') {
  const storedTheme = useStore.getState().theme;
  if (storedTheme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

export default useStore;
