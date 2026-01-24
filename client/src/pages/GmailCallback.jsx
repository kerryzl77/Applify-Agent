import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { gmailAPI } from '../services/api';
import { getSafeReturnTo } from '../utils/gmail';

const GmailCallback = () => {
  const navigate = useNavigate();
  const { search } = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(search);
    const status = params.get('status');
    const returnTo = getSafeReturnTo(params.get('return_to'));

    const finalize = async () => {
      if (status === 'connected') {
        toast.success('Gmail connected');
        try {
          await gmailAPI.status();
        } catch {
          // Ignore status refresh errors; user can retry later.
        }
      } else if (status === 'invalid_state') {
        toast.error('Gmail authorization expired. Try connecting again.');
      } else {
        toast.error('Gmail connection failed. Try again.');
      }

      navigate(returnTo || '/dashboard', { replace: true });
    };

    finalize();
  }, [navigate, search]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
      <div className="flex flex-col items-center gap-3 text-gray-600 dark:text-gray-300">
        <Loader2 className="w-6 h-6 animate-spin" />
        <p>Finalizing Gmail connection...</p>
      </div>
    </div>
  );
};

export default GmailCallback;
