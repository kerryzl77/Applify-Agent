import { Toaster } from 'react-hot-toast';

const Toast = () => {
  return (
    <Toaster
      position="top-right"
      reverseOrder={false}
      gutter={8}
      toastOptions={{
        duration: 4000,
        style: {
          background: 'var(--toast-bg)',
          color: 'var(--toast-text)',
          borderRadius: '0.75rem',
          border: '1px solid var(--toast-border)',
          padding: '16px',
          fontSize: '14px',
          maxWidth: '500px',
        },
        success: {
          iconTheme: {
            primary: '#10B981',
            secondary: '#fff',
          },
          style: {
            '--toast-bg': 'rgb(var(--color-white) / 1)',
            '--toast-text': 'rgb(var(--color-gray-900) / 1)',
            '--toast-border': 'rgb(var(--color-gray-200) / 1)',
          },
          className: 'dark:!bg-gray-800 dark:!text-gray-100 dark:!border-gray-700',
        },
        error: {
          iconTheme: {
            primary: '#EF4444',
            secondary: '#fff',
          },
          style: {
            '--toast-bg': 'rgb(var(--color-white) / 1)',
            '--toast-text': 'rgb(var(--color-gray-900) / 1)',
            '--toast-border': 'rgb(var(--color-gray-200) / 1)',
          },
          className: 'dark:!bg-gray-800 dark:!text-gray-100 dark:!border-gray-700',
        },
        loading: {
          iconTheme: {
            primary: '#3B82F6',
            secondary: '#fff',
          },
          style: {
            '--toast-bg': 'rgb(var(--color-white) / 1)',
            '--toast-text': 'rgb(var(--color-gray-900) / 1)',
            '--toast-border': 'rgb(var(--color-gray-200) / 1)',
          },
          className: 'dark:!bg-gray-800 dark:!text-gray-100 dark:!border-gray-700',
        },
      }}
    />
  );
};

export default Toast;
