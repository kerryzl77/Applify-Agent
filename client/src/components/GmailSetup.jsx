import { useEffect, useMemo } from "react";
import { MailCheck, MailWarning } from "lucide-react";
import { isGmailAuthorized } from "../utils/gmail";

const GmailSetup = ({ open, onClose, onConnected, gmailStatus, onConnect, onDisconnect }) => {
  useEffect(() => {
    if (!open) {
      return;
    }
    if (isGmailAuthorized(gmailStatus) && onConnected) {
      onConnected();
    }
  }, [open, gmailStatus, onConnected]);

  if (!open) {
    return null;
  }

  const statusVariant = useMemo(() => {
    if (isGmailAuthorized(gmailStatus)) {
      return "authorized";
    }
    if (gmailStatus?.availability === "configured") {
      return "configured";
    }
    if (gmailStatus?.availability === "unavailable") {
      return "unavailable";
    }
    return "unknown";
  }, [gmailStatus]);

  const renderBody = () => {
    if (statusVariant === "unavailable") {
      return (
        <div className="space-y-3 text-sm text-gray-600 dark:text-gray-300">
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <MailWarning className="w-5 h-5" />
            Gmail configuration missing
          </div>
          <p>
            Provide your Google OAuth client JSON via <code>config/gcp-oauth.keys.json</code>
            or set the <code>GCP_OAUTH_KEYS</code> environment variable and redeploy.
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
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Connect your Gmail account to create drafts automatically.
        </p>
        <button onClick={onConnect} className="btn btn-primary">
          Connect Gmail
        </button>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center px-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Gmail Setup
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
