import { useState, useEffect, useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  Copy,
  Download,
  RefreshCw,
  Loader2,
  FileText,
  Link as LinkIcon,
  User as UserIcon,
  Briefcase,
  Mail,
  Settings,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import useStore from "../store/useStore";
import { gmailAPI } from "../services/api";
import { copyToClipboard, downloadFile } from "../utils/helpers";
import toast from "react-hot-toast";
import ResumeUploader from "./ResumeUploader";
import axios from "axios";
import GmailSetup from "./GmailSetup";
import { Upload } from "lucide-react";

const ContentGenerator = () => {
  const {
    currentConversationId,
    conversations,
    isGenerating,
    setGenerating,
    resume,
    gmailStatus,
    setGmailStatus,
    isGmailSetupOpen,
    setGmailSetupOpen,
  } = useStore();

  const [inputType, setInputType] = useState("manual"); // 'url' or 'manual'
  const [formData, setFormData] = useState({
    url: "",
    manual_text: "",
    person_name: "",
    person_position: "",
    linkedin_url: "",
    recipient_email: "",
  });
  const [generatedContent, setGeneratedContent] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);
  const [emailMetadata, setEmailMetadata] = useState({
    subject: "",
    body: "",
    body_html: "",
    recipient_email: "",
  });
  const [creatingDraft, setCreatingDraft] = useState(false);
  const [showResumeUploader, setShowResumeUploader] = useState(false);
  const [resumeProgress, setResumeProgress] = useState(null);
  const [resumeTaskId, setResumeTaskId] = useState(null);

  const currentConversation = conversations.find(
    (c) => c.id === currentConversationId,
  );
  const conversationType = currentConversation?.type;
  const isEmailWorkflow = ["connection_email", "hiring_manager_email"].includes(
    conversationType,
  );
  const needsPersonInfo = [
    "connection_email",
    "hiring_manager_email",
    "linkedin_message",
  ].includes(conversationType);

  // Poll for resume progress
  useEffect(() => {
    if (!resumeTaskId) return;

    const pollProgress = setInterval(async () => {
      try {
        const response = await axios.get(
          `/api/resume-refinement-progress/${resumeTaskId}`,
          { withCredentials: true },
        );

        setResumeProgress(response.data);

        if (
          response.data.status === "completed" ||
          response.data.step === "completed"
        ) {
          clearInterval(pollProgress);
          setResumeTaskId(null);
          setGenerating(false);
          setResumeProgress(null); // Clear progress to show download buttons

          // Extract file info from the response data
          const responseData = response.data.data || response.data;
          if (responseData?.file_info) {
            console.log("Setting file info:", responseData.file_info);
            setFileInfo(responseData.file_info);
          }

          // Show recommendations if available
          const recommendations = responseData?.recommendations || [];
          if (recommendations.length > 0) {
            setGeneratedContent(recommendations.join("\n\n"));
          } else {
            setGeneratedContent(
              "Resume optimized successfully! Click download to get your tailored resume.",
            );
          }

          toast.success("Resume generated successfully!");
        } else if (
          response.data.status === "error" ||
          response.data.step === "error"
        ) {
          clearInterval(pollProgress);
          setResumeTaskId(null);
          setGenerating(false);
          toast.error(response.data.message || "Resume generation failed");
        }
      } catch (error) {
        console.error("Error polling progress:", error);
      }
    }, 1000);

    return () => clearInterval(pollProgress);
  }, [resumeTaskId, setGenerating]);

  const resetForm = () => {
    setFormData({
      url: "",
      manual_text: "",
      person_name: "",
      person_position: "",
      linkedin_url: "",
      recipient_email: "",
    });
    setGeneratedContent(null);
    setFileInfo(null);
    setResumeProgress(null);
    setEmailMetadata({
      subject: "",
      body: "",
      body_html: "",
      recipient_email: "",
    });
  };

  const handleCopy = async (content) => {
    const success = await copyToClipboard(content);
    if (success) {
      toast.success("Copied to clipboard!");
    } else {
      toast.error("Failed to copy");
    }
  };

  const handleDownload = (type, format = "docx") => {
    if (fileInfo) {
      window.open(`/api/download/${fileInfo.filename}`, "_blank");
      toast.success("Download started!");
    } else if (generatedContent) {
      const filename = `${type}_${Date.now()}.${format}`;
      const mimeType = format === "pdf" ? "application/pdf" : "text/plain";
      downloadFile(generatedContent, filename, mimeType);
      toast.success(`Downloaded as ${format.toUpperCase()}!`);
    }
  };

  const handleDownloadPDF = async () => {
    if (fileInfo && fileInfo.filename.endsWith(".docx")) {
      // Try to convert to PDF via backend
      try {
        const pdfFilename = fileInfo.filename.replace(".docx", ".pdf");
        window.open(`/api/convert-to-pdf/${fileInfo.filename}`, "_blank");
        toast.success("Converting to PDF...");
      } catch (error) {
        toast.error("PDF conversion failed. Download DOCX instead.");
      }
    } else if (fileInfo && fileInfo.filename.endsWith(".pdf")) {
      // Already a PDF
      window.open(`/api/download/${fileInfo.filename}`, "_blank");
      toast.success("Download started!");
    } else {
      toast.error("No file available for PDF download");
    }
  };

  const validateForm = () => {
    if (!resume) {
      toast.error("Please upload your resume first");
      return false;
    }

    const needsPersonInfo = [
      "connection_email",
      "hiring_manager_email",
      "linkedin_message",
    ].includes(conversationType);

    if (needsPersonInfo) {
      if (!formData.person_name || !formData.person_position) {
        toast.error("Please enter the person's name and position");
        return false;
      }
      if (
        ["connection_email", "hiring_manager_email"].includes(
          conversationType,
        ) &&
        !formData.recipient_email
      ) {
        toast.error("Please provide the recipient's email");
        return false;
      }
    } else {
      if (inputType === "url" && !formData.url) {
        toast.error("Please enter a job posting URL");
        return false;
      }
      if (inputType === "manual" && !formData.manual_text) {
        toast.error("Please enter the job description");
        return false;
      }
    }

    return true;
  };

  const refreshGmailStatus = useCallback(async () => {
    try {
      const response = await gmailAPI.status();
      setGmailStatus(response);
    } catch (error) {
      setGmailStatus({ availability: "unavailable", authorized: false, error: error.message });
    }
  }, [setGmailStatus]);

  useEffect(() => {
    refreshGmailStatus();
  }, [refreshGmailStatus]);

  useEffect(() => {
    if (!isEmailWorkflow) {
      return;
    }
    refreshGmailStatus();
  }, [isEmailWorkflow, refreshGmailStatus]);

  const handleConnectGmail = async () => {
    try {
      const { auth_url } = await gmailAPI.getAuthUrl();
      window.location.href = auth_url;
    } catch (error) {
      toast.error(error.message || "Failed to initiate Gmail authorization");
    }
  };

  const handleCreateDraft = async () => {
    if (!isEmailWorkflow) {
      return;
    }

    if (gmailStatus.availability === "unavailable") {
      toast.error("Gmail API is not configured");
      return;
    }

    if (gmailStatus.availability !== "authorized") {
      toast.error("Connect your Gmail account first");
      setGmailSetupOpen(true);
      return;
    }

    if (!emailMetadata.subject || !emailMetadata.body_html) {
      toast.error("Generate the email before creating a draft");
      return;
    }

    if (!emailMetadata.recipient_email) {
      toast.error("Recipient email is required");
      return;
    }

    try {
      setCreatingDraft(true);
      await gmailAPI.createDraft({
        recipient_email: emailMetadata.recipient_email,
        subject: emailMetadata.subject,
        body: emailMetadata.body_html,
      });
      toast.success("Draft created in Gmail");
    } catch (error) {
      toast.error(error.message || "Failed to create Gmail draft");
    } finally {
      setCreatingDraft(false);
    }
  };

  const handleGenerate = async () => {
    if (!validateForm() || isGenerating) return;

    setGenerating(true);
    setGeneratedContent(null);
    setFileInfo(null);
    setResumeProgress(null);

    try {
      let response;

      if (conversationType === "resume") {
        // Resume tailoring uses different endpoint
        const payload = {
          input_type: inputType,
          job_description:
            inputType === "manual" ? formData.manual_text : undefined,
          url: inputType === "url" ? formData.url : undefined,
        };

        response = await axios.post("/api/refine-resume", payload, {
          withCredentials: true,
        });

        if (response.data.task_id) {
          setResumeTaskId(response.data.task_id);
          setResumeProgress({
            status: "processing",
            message: "Starting resume generation...",
            progress: 0,
          });
        }
        return; // Exit here, polling will handle the rest
      } else {
        // Cover letter, email, connection messages
        const payload = {
          content_type: conversationType,
          input_type: inputType,
        };

        if (inputType === "url") {
          payload.url = formData.url;
        } else {
          payload.manual_text = formData.manual_text;
        }

        // Add person info for connection messages
        if (needsPersonInfo) {
          payload.person_name = formData.person_name;
          payload.person_position = formData.person_position;
          if (formData.linkedin_url) {
            payload.linkedin_url = formData.linkedin_url;
          }
          if (isEmailWorkflow && formData.recipient_email) {
            payload.recipient_email = formData.recipient_email;
          }
        }

        response = await axios.post("/api/generate", payload, {
          withCredentials: true,
        });

        setGeneratedContent(response.data.content);
        if (response.data.file_info) {
          setFileInfo(response.data.file_info);
        }

        if (isEmailWorkflow) {
          setEmailMetadata({
            subject: response.data.email_subject || "",
            body: response.data.content || "",
            body_html: response.data.email_html || "",
            recipient_email: formData.recipient_email || "",
          });
          refreshGmailStatus();
        }

        toast.success("Content generated successfully!");
      }
    } catch (error) {
      const errorMsg =
        error.response?.data?.error ||
        error.message ||
        "Failed to generate content";
      toast.error(errorMsg);
      setGeneratedContent(`Error: ${errorMsg}`);
    } finally {
      if (conversationType !== "resume") {
        setGenerating(false);
      }
    }
  };

  const handleRegenerate = () => {
    handleGenerate();
  };

  const handleDisconnectGmail = async () => {
    try {
      await gmailAPI.disconnect();
      toast.success("Gmail disconnected");
      refreshGmailStatus();
    } catch (error) {
      toast.error(error.message || "Failed to disconnect Gmail");
    }
  };

  const gmailStatusVariant = useMemo(() => {
    if (gmailStatus?.authorized) {
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

  const showGmailBanner = useMemo(
    () => ["connection_email", "hiring_manager_email"].includes(conversationType),
    [conversationType],
  );

  if (!currentConversationId) {
    return (
      <div className="h-full flex items-center justify-center bg-white dark:bg-gray-950">
        <div className="text-center p-8">
          <Sparkles className="w-16 h-16 mx-auto text-blue-500 mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Welcome to Applify
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Click "+" in the sidebar to create a new cover letter, email, or
            tailor your resume
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="h-full flex flex-col overflow-y-auto custom-scrollbar">
        <div className="flex-1 p-4 md:p-6 max-w-4xl mx-auto w-full">
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              {conversationType === "cover_letter" && "Generate Cover Letter"}
              {conversationType === "resume" && "Tailor Resume"}
              {conversationType === "connection_email" &&
                "Generate Connection Email"}
              {conversationType === "hiring_manager_email" &&
                "Generate Hiring Manager Email"}
              {conversationType === "linkedin_message" &&
                "Generate LinkedIn Message"}
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              {conversationType === "cover_letter" &&
                "Provide a job posting to generate a tailored cover letter"}
              {conversationType === "resume" &&
                "Provide a job posting to optimize your resume"}
              {needsPersonInfo &&
                "Enter the person's information to generate a personalized message"}
            </p>
          </div>

          {/* Resume Upload Reminder - Only show if no resume at all */}
          {!resume && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                  <Upload className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">
                    Resume Required
                  </h3>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
                    Upload your resume once to generate personalized cover
                    letters, emails, and tailored resumes. Your information will
                    be saved for all future generations.
                  </p>
                  <button
                    onClick={() => setShowResumeUploader(!showResumeUploader)}
                    className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline"
                  >
                    {showResumeUploader
                      ? "Hide Uploader ↑"
                      : "Upload Resume Now →"}
                  </button>
                </div>
              </div>
              {showResumeUploader && (
                <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-800">
                  <ResumeUploader
                    onUploadComplete={() => setShowResumeUploader(false)}
                  />
                </div>
              )}
            </motion.div>
          )}

          {/* Form */}
          <div className="card p-6 mb-6">
            {needsPersonInfo ? (
              /* Person Information Form */
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <UserIcon className="inline w-4 h-4 mr-1" />
                    Person Name *
                  </label>
                  <input
                    type="text"
                    value={formData.person_name}
                    onChange={(e) =>
                      setFormData({ ...formData, person_name: e.target.value })
                    }
                    placeholder="First Last"
                    className="input w-full"
                    disabled={isGenerating}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <Briefcase className="inline w-4 h-4 mr-1" />
                    Position / Company *
                  </label>
                  <input
                    type="text"
                    value={formData.person_position}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        person_position: e.target.value,
                      })
                    }
                    placeholder="Role at Company"
                    className="input w-full"
                    disabled={isGenerating}
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Format: "Position at Company"
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <LinkIcon className="inline w-4 h-4 mr-1" />
                    LinkedIn URL (Optional)
                  </label>
                  <input
                    type="url"
                    value={formData.linkedin_url}
                    onChange={(e) =>
                      setFormData({ ...formData, linkedin_url: e.target.value })
                    }
                    placeholder="https://linkedin.com/in/username"
                    className="input w-full"
                    disabled={isGenerating}
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Optional: Enhance with LinkedIn data
                  </p>
                </div>

                {["connection_email", "hiring_manager_email"].includes(
                  conversationType,
                ) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      <Mail className="inline w-4 h-4 mr-1" />
                      Recipient Email *
                    </label>
                    <input
                      type="email"
                      value={formData.recipient_email}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          recipient_email: e.target.value,
                        })
                      }
                      placeholder="contact@company.com"
                      className="input w-full"
                      disabled={isGenerating}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Used when creating Gmail drafts.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              /* Job Posting Form */
              <>
                {/* Input Type Toggle */}
                <div className="flex space-x-2 mb-4">
                  <button
                    onClick={() => setInputType("manual")}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                      inputType === "manual"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                    }`}
                    disabled={isGenerating}
                  >
                    <FileText className="inline w-4 h-4 mr-2" />
                    Paste Description
                  </button>
                  <button
                    onClick={() => setInputType("url")}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                      inputType === "url"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                    }`}
                    disabled={isGenerating}
                  >
                    <LinkIcon className="inline w-4 h-4 mr-2" />
                    Job URL
                  </button>
                </div>

                {inputType === "url" ? (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Job Posting URL
                    </label>
                    <input
                      type="url"
                      value={formData.url}
                      onChange={(e) =>
                        setFormData({ ...formData, url: e.target.value })
                      }
                      placeholder="https://jobs.company.com/posting..."
                      className="input w-full"
                      disabled={isGenerating}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Enter the direct link to the job posting
                    </p>
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Job Description
                    </label>
                    <textarea
                      value={formData.manual_text}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          manual_text: e.target.value,
                        })
                      }
                      placeholder="Paste the full job description here..."
                      className="input w-full min-h-[200px]"
                      rows={10}
                      disabled={isGenerating}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Paste the complete job description including requirements
                    </p>
                  </div>
                )}
              </>
            )}

            {/* Action Buttons */}
            <div className="flex space-x-3 mt-6">
              <motion.button
                onClick={handleGenerate}
                disabled={isGenerating || !resume}
                className="flex-1 btn btn-primary flex items-center justify-center space-x-2"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    <span>Generate</span>
                  </>
                )}
              </motion.button>

              {generatedContent && (
                <motion.button
                  onClick={resetForm}
                  className="btn btn-outline"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  New Request
                </motion.button>
              )}
              {generatedContent && isEmailWorkflow && (
                <div className="flex flex-col gap-2 w-full mt-4">
                  <button
                    onClick={handleCreateDraft}
                    disabled={creatingDraft || gmailStatus.availability !== "authorized"}
                    className="btn btn-secondary flex items-center justify-center gap-2"
                  >
                    {creatingDraft ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Creating Gmail Draft...
                      </>
                    ) : (
                      <>
                        <Mail className="w-4 h-4" />
                        Create Gmail Draft
                      </>
                    )}
                  </button>
                  {gmailStatus.availability === "authorized" ? (
                    <button
                      onClick={handleDisconnectGmail}
                      className="btn btn-outline flex items-center justify-center gap-2"
                    >
                      <Settings className="w-4 h-4" />
                      Disconnect Gmail
                    </button>
                  ) : (
                    <button
                      onClick={handleConnectGmail}
                      className="btn btn-outline flex items-center justify-center gap-2"
                    >
                      <Settings className="w-4 h-4" />
                      Connect Gmail
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Resume Progress */}
          {resumeProgress && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-6 mb-6"
            >
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Resume Generation Progress
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {resumeProgress.message}
                  </span>
                  <span className="text-sm font-medium text-blue-600">
                    {resumeProgress.progress}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${resumeProgress.progress}%` }}
                  />
                </div>
              </div>
            </motion.div>
          )}

          {/* Generated Content */}
          {generatedContent && !resumeProgress && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Generated Content
                </h3>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => handleCopy(generatedContent)}
                    className="btn btn-sm btn-outline flex items-center space-x-1"
                    title="Copy to clipboard"
                  >
                    <Copy className="w-4 h-4" />
                    <span>Copy</span>
                  </button>

                  {/* Download DOCX button */}
                  <button
                    onClick={() => handleDownload(conversationType, "docx")}
                    className="btn btn-sm bg-blue-600 text-white hover:bg-blue-700 flex items-center space-x-1"
                    title="Download as Word document"
                  >
                    <Download className="w-4 h-4" />
                    <span>DOCX</span>
                  </button>

                  {/* Download PDF button */}
                  {fileInfo ? (
                    <button
                      onClick={handleDownloadPDF}
                      className="btn btn-sm bg-red-600 text-white hover:bg-red-700 flex items-center space-x-1"
                      title="Download as PDF"
                    >
                      <FileText className="w-4 h-4" />
                      <span>PDF</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => handleDownload(conversationType, "pdf")}
                      className="btn btn-sm bg-red-600 text-white hover:bg-red-700 flex items-center space-x-1"
                      title="Download as PDF"
                    >
                      <FileText className="w-4 h-4" />
                      <span>PDF</span>
                    </button>
                  )}

                  <button
                    onClick={handleRegenerate}
                    disabled={isGenerating}
                    className="btn btn-sm btn-outline flex items-center space-x-1"
                    title="Regenerate content"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Regenerate</span>
                  </button>
                </div>
              </div>

              <div className="prose prose-sm dark:prose-invert max-w-none bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
                <ReactMarkdown>{generatedContent}</ReactMarkdown>
              </div>
            </motion.div>
          )}
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

export default ContentGenerator;
