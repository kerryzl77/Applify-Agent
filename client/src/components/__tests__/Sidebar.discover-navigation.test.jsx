import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import Sidebar from '../Sidebar';
import useStore from '../../store/useStore';

vi.mock('framer-motion', () => {
  const passthrough = ({ children, ...props }) => <div {...props}>{children}</div>;
  return {
    AnimatePresence: ({ children }) => <>{children}</>,
    motion: new Proxy(
      {},
      {
        get: () => passthrough,
      }
    ),
  };
});

vi.mock('../../services/api', () => ({
  authAPI: {
    logout: vi.fn().mockResolvedValue({ success: true }),
  },
}));

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('Sidebar desktop discover navigation', () => {
  beforeEach(() => {
    window.innerWidth = 1280;
    useStore.setState({
      user: {
        name: 'Test User',
        email: 'test@example.com',
      },
      isAuthenticated: true,
      conversations: [],
      currentConversationId: null,
    });
  });

  it('keeps the persistent desktop sidebar open when navigating to Discover Jobs', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.queryByTitle(/open menu/i)).toBeNull();

    fireEvent.click(screen.getByRole('link', { name: /discover jobs/i }));

    expect(screen.queryByTitle(/open menu/i)).toBeNull();
  });
});
