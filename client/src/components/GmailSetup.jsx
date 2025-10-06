import { useEffect, useState } from "react";
import axios from "axios";
import { Loader2, MailCheck, MailWarning } from "lucide-react";
import toast from "react-hot-toast";

const GmailSetup = ({ open, onClose, onConnected }) => {
  const [status, setStatus] = useState({
    available: false,
    authenticated: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    const fetchStatus = async () => {
      try {
        setLoading(true);
        const response = await axios.get("/api/gmail/status", {
          withCredentials: true,
        });
        setStatus(response.data);
        setError(null);
      } catch (err) {
        setStatus({ available: false, authenticated: false });
        setError(
          err.response?.data?.error || "Unable to reach Gmail MCP server.",
        );
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
  }, [open]);

  const handleConnect = async () => {
    try {
      setLoading(true);
      const response = await axios.get("/api/gmail/auth", {
        withCredentials: true,
      });
      const authUrl = response.data?.auth_url;

      if (!authUrl) {
        toast.error("Unable to initiate Gmail connection.");
        return;
      }

      window.location.href = authUrl;
    } catch (err) {
      toast.error(
        err.response?.data?.error || "Failed to start Gmail authentication",
      );
    } finally {
      setLoading(false);
    }
  };

  const renderBody = () => {
    if (loading) {
      return (
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
          <Loader2 className="w-4 h-4 animate-spin" />
          Checking Gmail integration...
        </div>
      );
    }

    if (!status.available) {
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <MailWarning className="w-5 h-5" />
            Gmail MCP not configured
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Set environment variables `MCP_SERVER_URL`, `GMAIL_CLIENT_ID`,
            `GMAIL_CLIENT_SECRET`, and `GMAIL_REDIRECT_URI`.
          </p>
          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>
      );
    }

    if (status.authenticated) {
      return (
        <div className="flex items-center gap-3 text-green-600 dark:text-green-400">
          <MailCheck className="w-5 h-5" />
          Gmail is connected.
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <div className="text-sm text-gray-600 dark:text-gray-300">
          Connect your Gmail account to automatically create drafts using the
          generated emails.
        </div>
        <button onClick={handleConnect} className="btn btn-primary">
          Connect Gmail
        </button>
      </div>
    );
  };

  const handleClose = () => {
    if (status.authenticated && onConnected) {
      onConnected();
    }
    onClose?.();
  };

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center px-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Gmail MCP Setup
          </h3>
          <button
            onClick={handleClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Close
          </button>
        </div>
        {renderBody()}
      </div>
    </div>
  );
};

export default GmailSetup;
