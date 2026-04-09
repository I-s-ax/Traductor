import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Toaster, toast } from "sonner";
import {
  FileUp,
  ArrowRightLeft,
  Download,
  History,
  Languages,
  Cpu,
  CheckCircle,
  AlertCircle,
  X,
  Loader2,
  FileText,
  Image as ImageIcon,
  Trash2,
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Provider icons with custom colors
const ProviderIcon = ({ provider, isActive }) => {
  const colors = {
    openai: "#10A37F",
    gemini: "#4285F4",
    claude: "#D97757",
  };

  return (
    <Cpu
      size={24}
      style={{ color: isActive ? colors[provider] : "#52525B" }}
      className="transition-colors duration-200"
    />
  );
};

function App() {
  const [file, setFile] = useState(null);
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("es");
  const [provider, setProvider] = useState("openai");
  const [languages, setLanguages] = useState([]);
  const [providers, setProviders] = useState([]);
  const [history, setHistory] = useState([]);
  const [isTranslating, setIsTranslating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [langRes, provRes, histRes] = await Promise.all([
          axios.get(`${API}/languages`),
          axios.get(`${API}/providers`),
          axios.get(`${API}/history`),
        ]);
        setLanguages(langRes.data);
        setProviders(provRes.data);
        setHistory(histRes.data);
      } catch (error) {
        console.error("Error fetching data:", error);
        toast.error("Error loading application data");
      }
    };
    fetchData();
  }, []);

  // Dropzone configuration
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      const validTypes = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
      ];
      if (!validTypes.includes(selectedFile.type)) {
        toast.error("Unsupported file type. Use PDF, PNG, JPG, or WEBP");
        return;
      }
      setFile(selectedFile);
      toast.success(`File selected: ${selectedFile.name}`);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/webp": [".webp"],
    },
    multiple: false,
  });

  // Swap languages
  const swapLanguages = () => {
    const temp = sourceLang;
    setSourceLang(targetLang);
    setTargetLang(temp);
  };

  // Handle translation
  const handleTranslate = async () => {
    if (!file) {
      toast.error("Please select a file first");
      return;
    }

    setIsTranslating(true);
    setProgress(0);
    setProgressMessage("Preparing file...");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_lang", sourceLang);
    formData.append("target_lang", targetLang);
    formData.append("provider", provider);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) return prev;
          const increment = Math.random() * 15;
          const newProgress = Math.min(prev + increment, 90);

          if (newProgress < 30) setProgressMessage("Extracting text...");
          else if (newProgress < 60) setProgressMessage("Translating with AI...");
          else if (newProgress < 90) setProgressMessage("Generating output...");

          return newProgress;
        });
      }, 500);

      const response = await axios.post(`${API}/translate`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      clearInterval(progressInterval);
      setProgress(100);
      setProgressMessage("Translation complete!");

      toast.success("Translation completed successfully!");

      // Refresh history
      const histRes = await axios.get(`${API}/history`);
      setHistory(histRes.data);

      // Auto-download
      setTimeout(() => {
        handleDownload(response.data.id);
      }, 500);
    } catch (error) {
      console.error("Translation error:", error);
      const errorMsg =
        error.response?.data?.detail || "Translation failed. Please try again.";
      toast.error(errorMsg);
    } finally {
      setIsTranslating(false);
      setProgress(0);
      setProgressMessage("");
      setFile(null);
    }
  };

  // Handle download
  const handleDownload = async (translationId) => {
    try {
      const response = await axios.get(`${API}/download/${translationId}`, {
        responseType: "blob",
      });

      const contentDisposition = response.headers["content-disposition"];
      let filename = "translated_document";
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/);
        if (match) filename = match[1];
      }

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success("Download started!");
    } catch (error) {
      console.error("Download error:", error);
      toast.error("Failed to download file");
    }
  };

  // Handle delete
  const handleDelete = async (translationId) => {
    try {
      await axios.delete(`${API}/history/${translationId}`);
      setHistory((prev) => prev.filter((item) => item.id !== translationId));
      toast.success("Deleted from history");
    } catch (error) {
      console.error("Delete error:", error);
      toast.error("Failed to delete");
    }
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Get language name
  const getLangName = (code) => {
    const lang = languages.find((l) => l.code === code);
    return lang ? lang.name : code;
  };

  return (
    <div className="app-container min-h-screen">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#0F0F0F",
            border: "1px solid #222222",
            color: "#F5F5F5",
            fontFamily: "IBM Plex Sans, sans-serif",
          },
        }}
      />

      {/* Header */}
      <header className="app-header glass-header" data-testid="app-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Languages className="text-[#D4FF00]" size={28} />
              <h1 className="text-xl sm:text-2xl font-black tracking-tighter text-[#F5F5F5]">
                TRANSLATE<span className="text-[#D4FF00]">HUB</span>
              </h1>
            </div>
            <span className="mono text-xs text-[#52525B] hidden sm:block">
              PDF & IMAGE TRANSLATOR
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-8"
        >
          {/* Title Section */}
          <div className="text-center mb-12">
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tighter text-[#F5F5F5] mb-4"
            >
              TRANSLATE YOUR DOCUMENTS
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-[#A1A1AA] text-base sm:text-lg font-light max-w-2xl mx-auto"
            >
              Upload PDF or images, select your languages, and let AI do the rest.
              Download your translated files instantly.
            </motion.p>
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
            {/* Left Column - File Upload */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="lg:col-span-2"
            >
              <p className="section-title">
                <FileUp size={14} className="inline mr-2" />
                UPLOAD FILE
              </p>

              <div
                {...getRootProps()}
                data-testid="file-upload-dropzone"
                className={`dropzone ${isDragActive ? "active dropzone-active" : ""}`}
              >
                <input {...getInputProps()} />
                <div className="dropzone-icon">
                  <FileUp size={48} />
                </div>
                <p className="mono text-sm text-[#A1A1AA] mb-2">
                  {isDragActive
                    ? "DROP YOUR FILE HERE"
                    : "DRAG & DROP PDF / IMAGES"}
                </p>
                <p className="text-xs text-[#52525B]">
                  or click to browse (PDF, PNG, JPG, WEBP)
                </p>
              </div>

              {/* File Preview */}
              <AnimatePresence>
                {file && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="file-preview"
                  >
                    <div className="file-preview-icon">
                      {file.type === "application/pdf" ? (
                        <FileText size={24} />
                      ) : (
                        <ImageIcon size={24} />
                      )}
                    </div>
                    <span className="file-preview-name">{file.name}</span>
                    <span className="file-preview-size">
                      {formatFileSize(file.size)}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                      }}
                      className="p-1 hover:bg-[#222222] transition-colors"
                    >
                      <X size={18} className="text-[#52525B]" />
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Progress Section */}
              <AnimatePresence>
                {isTranslating && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="progress-section mt-6"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="progress-text flex items-center gap-2">
                        <Loader2 size={16} className="spinner" />
                        {progressMessage}
                      </span>
                      <span className="mono text-[#D4FF00] text-sm">
                        {Math.round(progress)}%
                      </span>
                    </div>
                    <Progress
                      value={progress}
                      className="h-2 bg-[#222222] progress-glow"
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            {/* Right Column - Configuration */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="space-y-6"
            >
              {/* Language Selection */}
              <div className="config-card">
                <p className="section-title">
                  <Languages size={14} className="inline mr-2" />
                  LANGUAGES
                </p>

                <div className="space-y-4">
                  <div>
                    <label className="mono text-xs text-[#52525B] mb-2 block">
                      SOURCE
                    </label>
                    <Select
                      value={sourceLang}
                      onValueChange={setSourceLang}
                      data-testid="source-language-select"
                    >
                      <SelectTrigger className="w-full bg-[#0F0F0F] border-[#222222] text-[#F5F5F5] rounded-none">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#0F0F0F] border-[#222222] rounded-none">
                        <ScrollArea className="h-[200px]">
                          {languages.map((lang) => (
                            <SelectItem
                              key={lang.code}
                              value={lang.code}
                              className="text-[#F5F5F5] focus:bg-[#171717] focus:text-[#D4FF00]"
                            >
                              {lang.name}
                            </SelectItem>
                          ))}
                        </ScrollArea>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex justify-center">
                    <button
                      onClick={swapLanguages}
                      className="p-2 border border-[#222222] hover:border-[#D4FF00] hover:bg-[#121212] transition-all"
                      data-testid="swap-languages-btn"
                    >
                      <ArrowRightLeft size={18} className="text-[#A1A1AA]" />
                    </button>
                  </div>

                  <div>
                    <label className="mono text-xs text-[#52525B] mb-2 block">
                      TARGET
                    </label>
                    <Select
                      value={targetLang}
                      onValueChange={setTargetLang}
                      data-testid="target-language-select"
                    >
                      <SelectTrigger className="w-full bg-[#0F0F0F] border-[#222222] text-[#F5F5F5] rounded-none">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#0F0F0F] border-[#222222] rounded-none">
                        <ScrollArea className="h-[200px]">
                          {languages.map((lang) => (
                            <SelectItem
                              key={lang.code}
                              value={lang.code}
                              className="text-[#F5F5F5] focus:bg-[#171717] focus:text-[#D4FF00]"
                            >
                              {lang.name}
                            </SelectItem>
                          ))}
                        </ScrollArea>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Provider Selection */}
              <div className="config-card">
                <p className="section-title">
                  <Cpu size={14} className="inline mr-2" />
                  AI PROVIDER
                </p>

                <div className="grid grid-cols-3 gap-3">
                  {providers.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setProvider(p.id)}
                      data-testid={`provider-${p.id}-btn`}
                      className={`provider-card provider-${p.id} ${
                        provider === p.id ? "active" : ""
                      }`}
                    >
                      <ProviderIcon provider={p.id} isActive={provider === p.id} />
                      <span className="mono text-xs text-[#A1A1AA] provider-name">
                        {p.id.toUpperCase()}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Translate Button */}
              <Button
                onClick={handleTranslate}
                disabled={!file || isTranslating}
                data-testid="translate-submit-btn"
                className="btn-translate bg-[#D4FF00] hover:bg-[#C2E600] text-[#050505] font-bold rounded-none"
              >
                {isTranslating ? (
                  <>
                    <Loader2 size={18} className="mr-2 spinner" />
                    TRANSLATING...
                  </>
                ) : (
                  <>
                    <Languages size={18} className="mr-2" />
                    TRANSLATE NOW
                  </>
                )}
              </Button>
            </motion.div>
          </div>

          {/* History Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-12"
          >
            <p className="section-title">
              <History size={14} className="inline mr-2" />
              TRANSLATION HISTORY
            </p>

            {history.length === 0 ? (
              <div className="empty-state" data-testid="history-empty-state">
                <History size={32} className="mx-auto mb-3 text-[#52525B]" />
                <p className="empty-state-text">NO PREVIOUS TRANSLATIONS FOUND</p>
              </div>
            ) : (
              <div
                className="border border-[#222222] overflow-hidden"
                data-testid="history-table"
              >
                <div className="overflow-x-auto">
                  <table className="history-table">
                    <thead>
                      <tr className="bg-[#0F0F0F]">
                        <th>FILE</th>
                        <th>LANGUAGES</th>
                        <th>PROVIDER</th>
                        <th>DATE</th>
                        <th>STATUS</th>
                        <th>ACTIONS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((item) => (
                        <tr key={item.id} className="table-row-hover">
                          <td>
                            <div className="flex items-center gap-2">
                              {item.file_type === "pdf" ? (
                                <FileText size={16} className="text-[#D4FF00]" />
                              ) : (
                                <ImageIcon size={16} className="text-[#D4FF00]" />
                              )}
                              <span className="mono text-sm truncate max-w-[150px]">
                                {item.filename}
                              </span>
                            </div>
                          </td>
                          <td>
                            <span className="mono text-sm">
                              {getLangName(item.source_lang)} →{" "}
                              {getLangName(item.target_lang)}
                            </span>
                          </td>
                          <td>
                            <span
                              className="mono text-xs px-2 py-1"
                              style={{
                                background:
                                  item.provider === "openai"
                                    ? "rgba(16, 163, 127, 0.1)"
                                    : item.provider === "gemini"
                                    ? "rgba(66, 133, 244, 0.1)"
                                    : "rgba(217, 119, 87, 0.1)",
                                color:
                                  item.provider === "openai"
                                    ? "#10A37F"
                                    : item.provider === "gemini"
                                    ? "#4285F4"
                                    : "#D97757",
                              }}
                            >
                              {item.provider.toUpperCase()}
                            </span>
                          </td>
                          <td>
                            <span className="mono text-xs text-[#52525B]">
                              {new Date(item.created_at).toLocaleDateString()}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`status-badge ${
                                item.status === "completed"
                                  ? "status-completed"
                                  : "status-error"
                              }`}
                            >
                              {item.status === "completed" ? (
                                <CheckCircle size={12} className="inline mr-1" />
                              ) : (
                                <AlertCircle size={12} className="inline mr-1" />
                              )}
                              {item.status}
                            </span>
                          </td>
                          <td>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleDownload(item.id)}
                                data-testid={`download-result-btn-${item.id}`}
                                className="p-2 border border-[#222222] hover:border-[#D4FF00] hover:bg-[#121212] transition-all"
                                title="Download"
                              >
                                <Download size={14} className="text-[#A1A1AA]" />
                              </button>
                              <button
                                onClick={() => handleDelete(item.id)}
                                className="p-2 border border-[#222222] hover:border-red-500 hover:bg-red-500/10 transition-all"
                                title="Delete"
                              >
                                <Trash2 size={14} className="text-[#52525B]" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </motion.div>

          {/* Footer */}
          <footer className="text-center py-8 mt-12 border-t border-[#222222]">
            <p className="mono text-xs text-[#52525B]">
              POWERED BY AI · SUPPORTS 50+ LANGUAGES · NO FILE LIMITS
            </p>
          </footer>
        </motion.div>
      </main>
    </div>
  );
}

export default App;
