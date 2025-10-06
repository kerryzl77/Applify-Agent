import { useEffect, useMemo } from "react";
import { MailCheck, MailWarning, Settings } from "lucide-react";

const getStatusVariant = (gmailStatus = {}) => {
  if (gmailStatus.authorized) {
    return "authorized";
  }
  if (gmailStatus.availability === "configured") {
    return "configured";
  }
  if (gmailStatus.availability === "unavailable") {
    return "unavailable";
  }
  return "unknown";
};

const GmailSetup = ({ open, onClose, onConnected, gmailStatus, onConnect, onDisconnect }) => {
  useEffect(() => {
    if (!open) {
      return;
    }
    if (gmailStatus.authorized && onConnected) {
      onConnected();
    }
  }, [open, gmailStatus, onConnected]);

  if (!open) {
    return null;
  }

  const statusVariant = useMemo(() => getStatusVariant(gmailStatus), [gmailStatus]);
  const renderBody = () => {
    if (statusVariant === "unavailable") {
      return (
        <div className="space-y-3 text-sm text-gray-600 dark:text-gray-300">
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <MailWarning className="w-5 h-5" />
            Gmail configuration missing
          </div>
          <p>
            Upload a valid Google OAuth client JSON in settings or set the
            <code>GCP_OAUTH_KEYS</code> config variable.
          </p>
        </div>
      );
    }

    if (statusVariant === "authorized") {
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-3 text-green-600 dark:text-green-400">
            <MailCheck className="w-5 h-5" />
            Gmail is connected.
          </div>
          <button onClick={onDisconnect} className="btn btn-outline">
            Disconnect Gmail
          </button>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Connect your Gmail account to create drafts automatically.
            </p>
            <p className="text-xs text-gray-500 mt-1">
              You will be redirected to Google to grant the draft scope.
            </p>
          </div>
          {statusVariant === "configured" && (
            <span className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
              <Settings className="w-3 h-3" />
              OAuth ready
            </span>
          )}
        </div>
        <button onClick={onConnect} className="btn btn-primary">
          Sign in with Google
        </button>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center px-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Connect Gmail
          </h3>
          <button
            onClick={onClose}
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
