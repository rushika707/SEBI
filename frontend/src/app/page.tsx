"use client";

import React, { useState, useEffect } from "react";
import {
  LayoutDashboard,
  FileText,
  GitBranch,
  Network,
  Split,
  AlertTriangle,
  FileBadge,
  Lock,
  User as UserIcon,
  CheckCircle,
  Clock,
  ArrowRight,
  UploadCloud,
  Search,
  Database,
  Activity,
  Trash2,
  Plus,
  RefreshCw,
  Sliders,
  LogOut,
  Building,
  ChevronRight,
  Send,
  AlertCircle,
  FileCheck,
  Check,
  X
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { api, DashboardStats, Document, Task, Clause, Obligation } from "../lib/api";

const COLORS = ["#06b6d4", "#f59e0b", "#ef4444", "#10b981", "#6366f1"];

export default function Home() {
  // Authentication State
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginEmail, setLoginEmail] = useState("compliance@sebicopilot.com");
  const [loginPassword, setLoginPassword] = useState("password");
  const [userRole, setUserRole] = useState("Compliance Officer");
  const [userFullName, setUserFullName] = useState("Compliance Officer Primary");
  const [authError, setAuthError] = useState("");

  // Navigation State
  const [activeTab, setActiveTab] = useState("dashboard");

  // Data Loading States
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [gapsData, setGapsData] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);

  // Tab Specific States
  // RAG Search
  const [ragQuery, setRagQuery] = useState("");
  const [ragResponse, setRagResponse] = useState<any>(null);
  const [ragLoading, setRagLoading] = useState(false);

  // Document Upload
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadType, setUploadType] = useState("circular");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  // Version Diff Engine
  const [diffBaseId, setDiffBaseId] = useState<string>("");
  const [diffCompareId, setDiffCompareId] = useState<string>("");
  const [diffResult, setDiffResult] = useState<any>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  // Task Evidence & Verifications
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceDesc, setEvidenceDesc] = useState("");
  const [evidenceUploading, setEvidenceUploading] = useState(false);
  const [verifyComment, setVerifyComment] = useState("");

  // Notifications Sidebar Alerts
  const [notifications, setNotifications] = useState<any[]>([
    { id: 1, title: "New SEBI Circular Ingested", message: "SEBI Cyber Framework amendment has been parsed into 2 obligations.", type: "info" },
    { id: 2, title: "Compliance Gap Detected", message: "VAPT Audit evidence is missing for the Operations department.", type: "alert" }
  ]);

  // Load application core stats
  useEffect(() => {
    if (isLoggedIn) {
      loadAllData();
    }
  }, [isLoggedIn]);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [statsRes, docsRes, tasksRes, gapsRes, graphRes] = await Promise.all([
        api.getDashboardStats(),
        api.getDocuments(),
        api.getTasks(),
        api.getGaps(),
        api.getGraph()
      ]);
      setStats(statsRes);
      setDocuments(docsRes);
      setTasks(tasksRes);
      setGapsData(gapsRes);
      setGraphData(graphRes);
      
      // Auto-populate version diff defaults
      if (docsRes.length > 0) {
        setDiffBaseId(docsRes[0].id.toString());
        setDiffCompareId(docsRes[1] ? docsRes[1].id.toString() : docsRes[0].id.toString());
      }
    } catch (e) {
      console.error("Error loading application state:", e);
    } finally {
      setLoading(false);
    }
  };

  // ----------------------------------------------------
  // Event Handlers
  // ----------------------------------------------------
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await api.login({ email: loginEmail, password: loginPassword });
      if (res.access_token) {
        localStorage.setItem("token", res.access_token);
        setIsLoggedIn(true);
        setUserRole(res.user.role);
        setUserFullName(res.user.full_name);
      }
    } catch (err) {
      setAuthError("Authentication failed. Please verify credentials.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setIsLoggedIn(false);
  };

  const handleDocumentUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !uploadTitle) return;

    setIsUploading(true);
    setUploadProgress(20);
    
    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("title", uploadTitle);
    formData.append("file_type", uploadType);

    try {
      setUploadProgress(50);
      await api.uploadDocument(formData);
      setUploadProgress(100);
      
      // Reset forms
      setUploadTitle("");
      setUploadFile(null);
      
      // Success Alert Notification
      setNotifications(prev => [
        { id: Date.now(), title: "Upload Completed", message: `Document '${uploadTitle}' has been uploaded. Parsing started.`, type: "success" },
        ...prev
      ]);
      
      // Reload Data
      await loadAllData();
    } catch (e) {
      console.error("Upload failed", e);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleVersionDiff = async () => {
    if (!diffBaseId || !diffCompareId) return;
    setDiffLoading(true);
    try {
      const res = await api.getDiff({
        base_doc_id: parseInt(diffBaseId),
        compare_doc_id: parseInt(diffCompareId)
      });
      setDiffResult(res);
    } catch (e) {
      console.error("Diff failed", e);
    } finally {
      setDiffLoading(false);
    }
  };

  const handleRAGQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ragQuery.trim()) return;
    setRagLoading(true);
    try {
      const res = await api.ragQuery(ragQuery);
      setRagResponse(res);
    } catch (e) {
      console.error("RAG failed", e);
    } finally {
      setRagLoading(false);
    }
  };

  const handleUploadEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !evidenceFile) return;

    setEvidenceUploading(true);
    try {
      await api.uploadEvidence(selectedTask.id, evidenceFile, evidenceDesc);
      setEvidenceFile(null);
      setEvidenceDesc("");
      setSelectedTask(null);
      
      setNotifications(prev => [
        { id: Date.now(), title: "Evidence Submitted", message: `Verification files uploaded for task: '${selectedTask.title}'`, type: "info" },
        ...prev
      ]);

      await loadAllData();
    } catch (e) {
      console.error("Evidence upload failed", e);
    } finally {
      setEvidenceUploading(false);
    }
  };

  const handleVerifyEvidence = async (action: "approve" | "reject") => {
    if (!selectedTask) return;
    try {
      await api.verifyEvidence(selectedTask.id, action, verifyComment);
      setVerifyComment("");
      setSelectedTask(null);

      setNotifications(prev => [
        { id: Date.now(), title: "Verification Completed", message: `Task evidence has been ${action === 'approve' ? 'approved' : 'rejected'}.`, type: action === 'approve' ? 'success' : 'alert' },
        ...prev
      ]);

      await loadAllData();
    } catch (e) {
      console.error("Verification failed", e);
    }
  };

  // ----------------------------------------------------
  // RENDERING HELPERS
  // ----------------------------------------------------
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center p-4">
        {/* Glow Effects */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-900/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-900/10 rounded-full blur-3xl" />

        <div className="w-full max-w-md glass p-8 rounded-2xl relative z-10 border border-white/10 shadow-2xl">
          <div className="text-center mb-8">
            <div className="inline-flex p-3 bg-cyan-950/40 text-cyan-400 rounded-xl mb-4 border border-cyan-800/30">
              <Building className="w-8 h-8" />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight glow-text">SEBI CoPilot</h1>
            <p className="text-zinc-400 text-sm mt-2">Agentic AI Compliance Operating System</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            {authError && (
              <div className="p-3 bg-red-950/40 border border-red-800/30 rounded-lg text-red-400 text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <div>
              <label className="block text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-2">Compliance Officer Email</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-500">
                  <UserIcon className="w-4 h-4" />
                </span>
                <input
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-zinc-950/60 border border-zinc-800 rounded-xl text-white outline-none focus:border-cyan-500 transition-colors"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-2">Password</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-500">
                  <Lock className="w-4 h-4" />
                </span>
                <input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-zinc-950/60 border border-zinc-800 rounded-xl text-white outline-none focus:border-cyan-500 transition-colors"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-3 px-4 bg-cyan-600 hover:bg-cyan-500 text-zinc-950 font-bold rounded-xl transition-colors flex items-center justify-center gap-2 mt-6 cursor-pointer"
            >
              Sign In to Dashboard
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-zinc-800/80 text-center">
            <p className="text-zinc-500 text-xs">
              Demo Credentials: Use preloaded compliance account or modify fields.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-[#f4f4f5] flex">
      {/* SIDEBAR NAVIGATION */}
      <aside className="w-64 border-r border-zinc-800/80 bg-zinc-950/40 shrink-0 flex flex-col justify-between">
        <div>
          {/* Brand Logo */}
          <div className="p-6 border-b border-zinc-850 flex items-center gap-3">
            <div className="p-2 bg-cyan-950/40 text-cyan-400 rounded-lg border border-cyan-800/30">
              <Building className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-white tracking-wide">SEBI CoPilot</h2>
              <span className="text-[10px] text-cyan-400 font-medium uppercase tracking-wider">Compliance OS</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            {[
              { id: "dashboard", label: "Executive Dashboard", icon: LayoutDashboard },
              { id: "documents", label: "Circular Ingestion", icon: FileText },
              { id: "workflows", label: "Compliance Tasks", icon: GitBranch },
              { id: "gaps", label: "Gap Analysis & Scans", icon: AlertTriangle },
              { id: "diff", label: "Version Diff Engine", icon: Split },
              { id: "graph", label: "Knowledge Graph", icon: Network },
              { id: "rag", label: "Explainable AI (RAG)", icon: Search }
            ].map((link) => {
              const Icon = link.icon;
              const isActive = activeTab === link.id;
              return (
                <button
                  key={link.id}
                  onClick={() => setActiveTab(link.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer ${
                    isActive
                      ? "bg-cyan-500/10 text-cyan-400 border-l-2 border-cyan-500"
                      : "text-zinc-400 hover:bg-zinc-900/60 hover:text-white"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {link.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="p-4 border-t border-zinc-900">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-full bg-cyan-950/40 border border-cyan-800/30 flex items-center justify-center text-cyan-400 font-bold">
              {userFullName.charAt(0)}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-white truncate">{userFullName}</p>
              <p className="text-[10px] text-zinc-500 truncate uppercase tracking-wider">{userRole}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full py-2 px-3 border border-zinc-800 hover:bg-zinc-900 text-zinc-400 hover:text-white rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            Logout
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* TOP BAR / HEADER */}
        <header className="h-16 border-b border-zinc-900/80 bg-zinc-950/20 px-8 flex items-center justify-between z-10">
          <div className="flex items-center gap-4">
            <h1 className="font-bold text-white text-lg capitalize">{activeTab.replace("-", " ")} Workspace</h1>
            {loading && <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />}
          </div>

          <div className="flex items-center gap-6">
            <a
              href={api.exportReportUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-1.5 border border-cyan-900 hover:bg-cyan-950/30 text-cyan-400 rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 cursor-pointer"
            >
              <FileBadge className="w-3.5 h-3.5" />
              Export Audit PDF
            </a>
            
            <div className="h-5 w-[1px] bg-zinc-800" />
            
            <div className="relative">
              <button className="relative p-1.5 text-zinc-400 hover:text-white transition-colors cursor-pointer">
                <Activity className="w-5 h-5" />
                <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-cyan-500 rounded-full ring-2 ring-[#09090b]" />
              </button>
            </div>
          </div>
        </header>

        {/* WORKSPACE CONTENT BODY */}
        <div className="flex-1 overflow-y-auto p-8 relative">
          {/* TAB 1: EXECUTIVE DASHBOARD */}
          {activeTab === "dashboard" && stats && (
            <div className="space-y-6">
              {/* Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                {[
                  { title: "Compliance Score", value: `${stats.compliance_score.toFixed(1)}%`, icon: FileCheck, color: "text-cyan-400" },
                  { title: "Pending Obligations", value: stats.pending_obligations, icon: Clock, color: "text-amber-400" },
                  { title: "Recent Circulars Ingested", value: stats.recent_circular_count, icon: FileText, color: "text-indigo-400" },
                  { title: "High-Risk Pending Tasks", value: stats.high_risk_pending, icon: AlertTriangle, color: "text-red-400" }
                ].map((card, i) => {
                  const Icon = card.icon;
                  return (
                    <div key={i} className="glass-card p-6 flex items-center justify-between">
                      <div>
                        <span className="text-zinc-500 text-xs font-semibold uppercase tracking-wider">{card.title}</span>
                        <h3 className="text-3xl font-extrabold text-white mt-2">{card.value}</h3>
                      </div>
                      <div className={`p-3 bg-zinc-900/60 rounded-xl border border-zinc-800 ${card.color}`}>
                        <Icon className="w-6 h-6" />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Diagrams and lists */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Department performance chart */}
                <div className="glass-card p-6 lg:col-span-2">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-6 flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-cyan-400" />
                    Department Compliance Performance
                  </h3>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats.department_performance}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                        <XAxis dataKey="name" stroke="#a1a1aa" />
                        <YAxis stroke="#a1a1aa" />
                        <Tooltip contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", color: "#fff" }} />
                        <Bar dataKey="compliance_rate" name="Compliance Rate (%)" fill="#06b6d4" radius={[4, 4, 0, 0]}>
                          {stats.department_performance.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Risk Distribution donut */}
                <div className="glass-card p-6">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-6 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-cyan-400" />
                    Risk Heatmap Distribution
                  </h3>
                  <div className="h-48 w-full flex justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={Object.entries(stats.risk_distribution).map(([key, val]) => ({ name: key, value: val }))}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          <Cell fill="#ef4444" />
                          <Cell fill="#f59e0b" />
                          <Cell fill="#06b6d4" />
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", color: "#fff" }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex justify-around text-xs mt-4">
                    <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-red-500 rounded-full" /> High</span>
                    <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-amber-500 rounded-full" /> Medium</span>
                    <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-cyan-500 rounded-full" /> Low</span>
                  </div>
                </div>
              </div>

              {/* Deadlines list */}
              <div className="glass-card p-6">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-6">Upcoming Task Deadlines</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800 text-zinc-500 font-semibold">
                        <th className="pb-3">Task Title</th>
                        <th className="pb-3">Responsible Dept</th>
                        <th className="pb-3">Due Date</th>
                        <th className="pb-3">Risk Level</th>
                        <th className="pb-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/60">
                      {stats.upcoming_deadlines.map((deadline, idx) => (
                        <tr key={idx} className="hover:bg-zinc-900/20 text-zinc-300">
                          <td className="py-3.5 font-medium text-white">{deadline.title}</td>
                          <td className="py-3.5">{deadline.department}</td>
                          <td className="py-3.5 flex items-center gap-2">
                            <Clock className="w-3.5 h-3.5 text-zinc-500" />
                            {deadline.due_date}
                          </td>
                          <td className="py-3.5">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              deadline.risk_level === 'High' ? 'bg-red-950/40 text-red-400 border border-red-900/30' : 'bg-amber-950/40 text-amber-400 border border-amber-900/30'
                            }`}>
                              {deadline.risk_level}
                            </span>
                          </td>
                          <td className="py-3.5 text-right">
                            <button
                              onClick={() => { setActiveTab("workflows") }}
                              className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 ml-auto cursor-pointer"
                            >
                              Open Board
                              <ChevronRight className="w-3 h-3" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: DOCUMENT UPLOAD & PARSING */}
          {activeTab === "documents" && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="glass-card p-8">
                <h3 className="text-lg font-bold text-white mb-6">Ingest New SEBI Circular</h3>
                
                <form onSubmit={handleDocumentUpload} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-2">Regulation Title</label>
                      <input
                        type="text"
                        value={uploadTitle}
                        onChange={(e) => setUploadTitle(e.target.value)}
                        placeholder="e.g. Master Circular for Investment Advisors"
                        className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-xl text-white outline-none focus:border-cyan-500 transition-colors text-sm"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-2">Circular Type</label>
                      <select
                        value={uploadType}
                        onChange={(e) => setUploadType(e.target.value)}
                        className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-xl text-white outline-none focus:border-cyan-500 transition-colors text-sm"
                      >
                        <option value="circular">Circular</option>
                        <option value="notification">Notification</option>
                        <option value="master_circular">Master Circular</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-2">Document File (PDF or Text)</label>
                    <div className="border-2 border-dashed border-zinc-800 rounded-2xl p-8 text-center hover:border-cyan-500/50 transition-colors relative cursor-pointer">
                      <input
                        type="file"
                        onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        required
                      />
                      <UploadCloud className="w-12 h-12 text-zinc-500 mx-auto mb-4" />
                      <p className="text-zinc-300 font-semibold text-sm">
                        {uploadFile ? uploadFile.name : "Drag & Drop or Click to browse"}
                      </p>
                      <p className="text-zinc-500 text-xs mt-2">Supports PDF, TXT files up to 15MB</p>
                    </div>
                  </div>

                  {isUploading && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs font-semibold text-cyan-400">
                        <span>Agent Pipeline Running...</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden">
                        <div className="h-full bg-cyan-500 transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
                      </div>
                      <p className="text-zinc-500 text-[10px]">
                        Parsing PDF → Segmenting Clauses → Extracting Obligations → Generating Checklists
                      </p>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isUploading}
                    className="py-3 px-6 bg-cyan-600 hover:bg-cyan-500 text-zinc-950 font-bold rounded-xl transition-colors cursor-pointer flex items-center gap-2 justify-center disabled:opacity-50"
                  >
                    Compile Regulations to Workflows
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </form>
              </div>

              {/* Ingested circulars table */}
              <div className="glass-card p-6">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-6">Previously Ingested Regulations</h3>
                <div className="divide-y divide-zinc-850">
                  {documents.map((doc) => (
                    <div key={doc.id} className="py-4 flex items-center justify-between">
                      <div className="flex items-center gap-3.5">
                        <div className="p-2.5 bg-zinc-900 rounded-lg text-zinc-400 border border-zinc-800">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-white text-sm">{doc.title}</h4>
                          <div className="flex items-center gap-3 text-xs text-zinc-500 mt-1">
                            <span className="capitalize">{doc.file_type.replace("_", " ")}</span>
                            <span>•</span>
                            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>

                      <div>
                        <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                          doc.status === 'parsed' ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/30' : 'bg-amber-950/40 text-amber-400 border border-amber-900/30'
                        }`}>
                          {doc.status.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: WORKFLOWS BOARD */}
          {activeTab === "workflows" && (
            <div className="space-y-6">
              {/* Dynamic checklist workflow builder columns */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Column 1: Pending Tasks */}
                <div className="glass-card p-5">
                  <div className="flex items-center justify-between mb-5">
                    <h3 className="font-bold text-white text-sm uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2.5 h-2.5 bg-amber-500 rounded-full" />
                      Assigned Checklist Items ({tasks.filter(t => t.status === 'pending').length})
                    </h3>
                  </div>

                  <div className="space-y-4">
                    {tasks.filter(t => t.status === 'pending').map((task) => (
                      <div
                        key={task.id}
                        onClick={() => setSelectedTask(task)}
                        className="p-4 bg-zinc-950/50 border border-zinc-850 rounded-xl hover:border-cyan-500/40 hover:bg-zinc-950 transition-all cursor-pointer"
                      >
                        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                          {task.obligation?.risk_level} Risk
                        </span>
                        <h4 className="font-bold text-white text-sm mt-1">{task.title}</h4>
                        <p className="text-zinc-400 text-xs mt-2 line-clamp-2">{task.description}</p>
                        
                        <div className="flex justify-between items-center mt-4 pt-3 border-t border-zinc-900">
                          <span className="text-zinc-500 text-[10px]">{task.obligation?.deadline}</span>
                          <span className="text-cyan-400 text-xs font-semibold flex items-center gap-1">
                            Upload Evidence
                            <ChevronRight className="w-3 h-3" />
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Column 2: In Verification Reviews */}
                <div className="glass-card p-5">
                  <div className="flex items-center justify-between mb-5">
                    <h3 className="font-bold text-white text-sm uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2.5 h-2.5 bg-cyan-500 rounded-full" />
                      Under Compliance Verification ({tasks.filter(t => t.status === 'in_progress').length})
                    </h3>
                  </div>

                  <div className="space-y-4">
                    {tasks.filter(t => t.status === 'in_progress').map((task) => (
                      <div
                        key={task.id}
                        onClick={() => setSelectedTask(task)}
                        className="p-4 bg-zinc-950/50 border border-zinc-850 rounded-xl hover:border-cyan-500/40 hover:bg-zinc-950 transition-all cursor-pointer"
                      >
                        <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider">
                          PENDING APPROVAL
                        </span>
                        <h4 className="font-bold text-white text-sm mt-1">{task.title}</h4>
                        <p className="text-zinc-400 text-xs mt-2 line-clamp-2">{task.description}</p>

                        <div className="flex justify-between items-center mt-4 pt-3 border-t border-zinc-900">
                          <span className="text-zinc-500 text-[10px]">{task.obligation?.deadline}</span>
                          <span className="text-cyan-400 text-xs font-semibold flex items-center gap-1">
                            Verify Files
                            <ChevronRight className="w-3 h-3" />
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Column 3: Approved & Compliant */}
                <div className="glass-card p-5">
                  <div className="flex items-center justify-between mb-5">
                    <h3 className="font-bold text-white text-sm uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full" />
                      Completed & Compliant ({tasks.filter(t => t.status === 'completed').length})
                    </h3>
                  </div>

                  <div className="space-y-4">
                    {tasks.filter(t => t.status === 'completed').map((task) => (
                      <div
                        key={task.id}
                        className="p-4 bg-zinc-950/20 border border-zinc-900 rounded-xl opacity-75"
                      >
                        <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" /> VERIFIED COMPLIANT
                        </span>
                        <h4 className="font-bold text-white text-sm mt-1">{task.title}</h4>
                        <p className="text-zinc-500 text-xs mt-2 line-clamp-2">{task.description}</p>

                        <div className="flex justify-between items-center mt-4 pt-3 border-t border-zinc-900/60">
                          <span className="text-zinc-500 text-[10px]">{task.obligation?.deadline}</span>
                          <span className="text-emerald-500 text-xs font-semibold flex items-center gap-1">
                            Compliant
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Task workflow modal for uploading evidence or verifying */}
              {selectedTask && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 animate-fade-in">
                  <div className="w-full max-w-2xl bg-zinc-950 border border-zinc-800 rounded-2xl p-6 shadow-2xl relative">
                    <button
                      onClick={() => setSelectedTask(null)}
                      className="absolute top-4 right-4 text-zinc-400 hover:text-white cursor-pointer"
                    >
                      <X className="w-5 h-5" />
                    </button>

                    <span className="text-xs text-zinc-500 font-semibold uppercase tracking-wider">
                      Obligation Code: {selectedTask.obligation?.clause_id || "Gen"}
                    </span>
                    <h3 className="text-xl font-bold text-white mt-1">{selectedTask.title}</h3>
                    
                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-zinc-300">
                      <div>
                        <p className="text-zinc-500 text-xs font-bold uppercase tracking-wider">Applicability</p>
                        <p className="mt-1">{selectedTask.obligation?.applicability}</p>
                      </div>
                      <div>
                        <p className="text-zinc-500 text-xs font-bold uppercase tracking-wider">Audit Frequency</p>
                        <p className="mt-1">{selectedTask.obligation?.frequency}</p>
                      </div>
                    </div>

                    <div className="mt-5">
                      <p className="text-zinc-500 text-xs font-bold uppercase tracking-wider">Operational Description</p>
                      <p className="text-zinc-300 text-sm mt-1">{selectedTask.description}</p>
                    </div>

                    <div className="mt-5 p-3.5 bg-cyan-950/20 border border-cyan-900/30 rounded-xl">
                      <p className="text-cyan-400 text-xs font-bold uppercase tracking-wider">Audit Evidence Required</p>
                      <p className="text-zinc-300 text-sm mt-1">{selectedTask.evidence_required}</p>
                    </div>

                    {/* Action form */}
                    <div className="mt-6 pt-6 border-t border-zinc-900">
                      {selectedTask.status === "pending" ? (
                        <form onSubmit={handleUploadEvidence} className="space-y-4">
                          <h4 className="font-bold text-white text-sm">Submit Compliance Evidence</h4>
                          
                          <div>
                            <label className="block text-zinc-400 text-xs mb-1.5">Evidence Description</label>
                            <input
                              type="text"
                              value={evidenceDesc}
                              onChange={(e) => setEvidenceDesc(e.target.value)}
                              placeholder="e.g. CISO designation letter board draft copy"
                              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-white text-sm outline-none"
                              required
                            />
                          </div>

                          <div>
                            <label className="block text-zinc-400 text-xs mb-1.5">Upload Verification File</label>
                            <input
                              type="file"
                              onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
                              className="w-full text-zinc-400 text-sm file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-zinc-800 file:text-white hover:file:bg-zinc-700"
                              required
                            />
                          </div>

                          <button
                            type="submit"
                            disabled={evidenceUploading}
                            className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 text-zinc-950 font-bold rounded-lg text-sm cursor-pointer"
                          >
                            {evidenceUploading ? "Uploading..." : "Upload Evidence"}
                          </button>
                        </form>
                      ) : (
                        <div className="space-y-4">
                          <h4 className="font-bold text-white text-sm">Review Submitted Evidence</h4>
                          {selectedTask.evidence_items && selectedTask.evidence_items.length > 0 && (
                            <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg flex items-center justify-between">
                              <span className="text-sm font-semibold text-white">
                                {selectedTask.evidence_items[selectedTask.evidence_items.length - 1].filename}
                              </span>
                              <span className="text-zinc-400 text-xs">
                                Uploaded by Staff
                              </span>
                            </div>
                          )}

                          {userRole === "Compliance Officer" || userRole === "Compliance Manager" || userRole === "Admin" ? (
                            <div className="space-y-3">
                              <textarea
                                value={verifyComment}
                                onChange={(e) => setVerifyComment(e.target.value)}
                                placeholder="Compliance audit verification comments (optional)..."
                                className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-lg text-white text-sm outline-none"
                              />

                              <div className="grid grid-cols-2 gap-3">
                                <button
                                  onClick={() => handleVerifyEvidence("approve")}
                                  className="py-2 bg-emerald-600 hover:bg-emerald-500 text-zinc-950 font-bold rounded-lg text-sm cursor-pointer"
                                >
                                  Approve & Verify
                                </button>
                                <button
                                  onClick={() => handleVerifyEvidence("reject")}
                                  className="py-2 bg-red-600 hover:bg-red-500 text-white font-bold rounded-lg text-sm cursor-pointer"
                                >
                                  Reject & Redo
                                </button>
                              </div>
                            </div>
                          ) : (
                            <p className="text-zinc-500 text-xs">
                              You do not have Compliance Officer permissions to approve or reject compliance evidence.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: GAP DETECTION ANALYSIS */}
          {activeTab === "gaps" && gapsData && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="glass-card p-6 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-white">Compliance Score Scan</h3>
                  <p className="text-zinc-400 text-sm mt-1">Real-time delta metrics scanner against expectations.</p>
                </div>
                <div className="text-right">
                  <span className="text-zinc-500 text-xs uppercase font-bold">Current Score</span>
                  <h2 className="text-4xl font-extrabold text-cyan-400 glow-text mt-1">{gapsData.compliance_score.toFixed(1)}%</h2>
                </div>
              </div>

              {/* Gaps List */}
              <div className="glass-card p-6">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-6 flex items-center gap-2">
                  <AlertCircle className="w-4.5 h-4.5 text-cyan-400" />
                  Identified Gaps ({gapsData.gap_count})
                </h3>

                <div className="space-y-4">
                  {gapsData.gaps.map((gap: any, idx: number) => (
                    <div key={idx} className="p-4 bg-zinc-950/40 border border-zinc-900 rounded-xl flex items-start gap-4">
                      <div className="p-2 bg-red-950/20 text-red-400 rounded-lg border border-red-900/30 mt-0.5">
                        <AlertTriangle className="w-4.5 h-4.5" />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-center gap-3">
                          <h4 className="font-semibold text-white text-sm truncate">{gap.obligation_title}</h4>
                          <span className="px-2 py-0.5 rounded bg-red-950/40 text-red-400 border border-red-900/30 text-[10px] font-bold uppercase shrink-0">
                            {gap.risk_level} Risk
                          </span>
                        </div>
                        <p className="text-zinc-300 text-xs mt-1.5 font-medium">{gap.task_title}</p>
                        <p className="text-zinc-400 text-xs mt-1">{gap.message}</p>
                      </div>
                    </div>
                  ))}

                  {gapsData.gap_count === 0 && (
                    <div className="p-8 text-center text-zinc-500 text-sm">
                      <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
                      No compliance gaps found. Your organization is 100% compliant!
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: VERSION DIFF ENGINE */}
          {activeTab === "diff" && (
            <div className="space-y-6">
              <div className="glass-card p-6">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-5">Compare SEBI Circular Versions</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-end">
                  <div>
                    <label className="block text-zinc-400 text-xs font-semibold mb-2">Base Document (Version A)</label>
                    <select
                      value={diffBaseId}
                      onChange={(e) => setDiffBaseId(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-white text-sm outline-none focus:border-cyan-500"
                    >
                      {documents.map((d) => (
                        <option key={d.id} value={d.id}>{d.title}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-zinc-400 text-xs font-semibold mb-2">Compare Document (Version B)</label>
                    <select
                      value={diffCompareId}
                      onChange={(e) => setDiffCompareId(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-white text-sm outline-none focus:border-cyan-500"
                    >
                      {documents.map((d) => (
                        <option key={d.id} value={d.id}>{d.title}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={handleVersionDiff}
                    disabled={diffLoading}
                    className="py-2.5 px-4 bg-cyan-600 hover:bg-cyan-500 text-zinc-950 font-bold rounded-lg text-sm cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {diffLoading ? "Comparing..." : "Execute Side-by-Side Diff"}
                    <Split className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {diffResult && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Detailed changes list */}
                  <div className="glass-card p-6 lg:col-span-2 space-y-4">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-2">Clause Side-by-Side View</h3>
                    
                    <div className="space-y-4 overflow-y-auto max-h-[500px] pr-2">
                      {diffResult.diffs.map((d: any, idx: number) => {
                        let badgeColor = "bg-zinc-800 text-zinc-400";
                        if (d.change_type === "modified") badgeColor = "bg-amber-950/40 text-amber-400 border border-amber-900/30";
                        if (d.change_type === "added") badgeColor = "bg-emerald-950/40 text-emerald-400 border border-emerald-900/30";
                        if (d.change_type === "deleted") badgeColor = "bg-red-950/40 text-red-400 border border-red-900/30";

                        return (
                          <div key={idx} className="p-4 bg-zinc-950/50 border border-zinc-900 rounded-xl space-y-3">
                            <div className="flex justify-between items-center">
                              <span className="font-bold text-white text-sm">Clause {d.clause_number}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${badgeColor}`}>
                                {d.change_type}
                              </span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                              <div className="space-y-1">
                                <p className="text-zinc-500 font-semibold uppercase">Base Version</p>
                                <p className="p-2.5 bg-zinc-950 border border-zinc-850 rounded text-zinc-400 min-h-[50px] whitespace-pre-line">
                                  {d.base_content || "[CLAUSE NOT IN BASE DOCUMENT]"}
                                </p>
                              </div>
                              <div className="space-y-1">
                                <p className="text-zinc-500 font-semibold uppercase">Compare Version</p>
                                <p className="p-2.5 bg-zinc-950 border border-zinc-850 rounded text-zinc-400 min-h-[50px] whitespace-pre-line">
                                  {d.compare_content || "[CLAUSE DELETED FROM NEW DOCUMENT]"}
                                </p>
                              </div>
                            </div>
                            {(d.timeline_changed || d.penalty_changed) && (
                              <div className="flex gap-2.5">
                                {d.timeline_changed && (
                                  <span className="px-2 py-0.5 rounded bg-amber-950/30 text-amber-400 border border-amber-900/20 text-[10px] font-bold">
                                    [TIMELINE AMENDED]
                                  </span>
                                )}
                                {d.penalty_changed && (
                                  <span className="px-2 py-0.5 rounded bg-red-950/30 text-red-400 border border-red-900/20 text-[10px] font-bold">
                                    [PENALTY MODIFIED]
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Impact Summary */}
                  <div className="glass-card p-6">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
                      <FileBadge className="w-4 h-4 text-cyan-400" />
                      AI Executive Impact Summary
                    </h3>
                    <div className="prose prose-invert prose-xs text-zinc-300 whitespace-pre-wrap leading-relaxed text-sm bg-zinc-950/30 border border-zinc-900 p-4 rounded-xl">
                      {diffResult.impact_summary}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: KNOWLEDGE GRAPH */}
          {activeTab === "graph" && (
            <div className="space-y-6">
              <div className="glass-card p-6">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-1">Interactive Compliance Knowledge Graph</h3>
                <p className="text-zinc-400 text-xs mb-6">Real-time traversal showing links from Regulation → Clause → Obligation → Assigned Department.</p>
                
                {/* SVG Visualizer */}
                <div className="h-[450px] bg-zinc-950 border border-zinc-900 rounded-xl relative overflow-hidden flex items-center justify-center">
                  <div className="absolute top-4 left-4 p-3 bg-zinc-900/80 rounded-xl border border-zinc-800 text-[11px] space-y-1.5 z-10">
                    <p className="font-bold text-white uppercase mb-2">Legend</p>
                    <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 bg-indigo-500 rounded-full" /> Regulation</span>
                    <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 bg-cyan-500 rounded-full" /> Clause</span>
                    <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 bg-red-500 rounded-full" /> Obligation</span>
                    <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 bg-emerald-500 rounded-full" /> Department</span>
                  </div>

                  <svg className="w-full h-full">
                    {/* Draw Links */}
                    {graphData.edges.map((edge: any, i: number) => {
                      const sourceNode = graphData.nodes.find((n: any) => n.id === edge.source);
                      const targetNode = graphData.nodes.find((n: any) => n.id === edge.target);
                      if (!sourceNode || !targetNode) return null;
                      
                      // Calculate static layout points for mock rendering
                      const sIdx = graphData.nodes.indexOf(sourceNode);
                      const tIdx = graphData.nodes.indexOf(targetNode);
                      
                      const sx = 150 + (sIdx % 3) * 150;
                      const sy = 100 + Math.floor(sIdx / 3) * 100;
                      
                      const tx = 150 + (tIdx % 3) * 150;
                      const ty = 100 + Math.floor(tIdx / 3) * 100;

                      return (
                        <g key={i}>
                          <line
                            x1={sx}
                            y1={sy}
                            x2={tx}
                            y2={ty}
                            stroke="#3f3f46"
                            strokeWidth="1.5"
                            strokeDasharray={edge.type === 'HAS_CLAUSE' ? "0" : "4"}
                          />
                          <text x={(sx+tx)/2} y={(sy+ty)/2 - 5} fill="#71717a" fontSize="8" textAnchor="middle">{edge.type}</text>
                        </g>
                      );
                    })}

                    {/* Draw Nodes */}
                    {graphData.nodes.map((node: any, i: number) => {
                      const x = 150 + (i % 3) * 150;
                      const y = 100 + Math.floor(i / 3) * 100;
                      
                      let color = "#6366f1"; // Indigo
                      if (node.label === "Clause") color = "#06b6d4"; // Cyan
                      if (node.label === "Obligation") color = "#ef4444"; // Red
                      if (node.label === "Department") color = "#10b981"; // Emerald

                      return (
                        <g key={node.id} className="cursor-pointer group">
                          <circle cx={x} cy={y} r="22" fill={color} opacity="0.15" stroke={color} strokeWidth="2" className="transition-transform group-hover:scale-110" />
                          <circle cx={x} cy={y} r="8" fill={color} />
                          <text x={x} y={y + 35} fill="#ffffff" fontSize="10" fontWeight="bold" textAnchor="middle" className="glow-text">
                            {node.properties.title ? node.properties.title.substring(0, 15) + "..." : node.properties.name || "Node"}
                          </text>
                          <text x={x} y={y - 30} fill="#71717a" fontSize="8" textAnchor="middle">
                            {node.label}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: EXPLAINABLE AI CHAT (RAG) */}
          {activeTab === "rag" && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="glass-card p-6">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-2">Natural Language Search & Advisory</h3>
                <p className="text-zinc-400 text-xs mb-5">Search compliant regulations and query citations directly utilizing Hybrid RAG search pipelines.</p>

                <form onSubmit={handleRAGQuery} className="flex gap-3">
                  <div className="relative flex-1">
                    <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-500">
                      <Search className="w-4 h-4" />
                    </span>
                    <input
                      type="text"
                      value={ragQuery}
                      onChange={(e) => setRagQuery(e.target.value)}
                      placeholder="e.g. What are the CISO filing requirements under SEBI rules?"
                      className="w-full pl-10 pr-4 py-3 bg-zinc-950 border border-zinc-800 rounded-xl text-white outline-none focus:border-cyan-500 transition-colors text-sm"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={ragLoading}
                    className="py-3 px-6 bg-cyan-600 hover:bg-cyan-500 text-zinc-950 font-bold rounded-xl transition-colors cursor-pointer flex items-center gap-2 disabled:opacity-50"
                  >
                    {ragLoading ? "Scanning RAG..." : "Query AI"}
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>

              {ragResponse && (
                <div className="space-y-6">
                  {/* Generative Answer */}
                  <div className="glass-card p-6 space-y-4">
                    <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Database className="w-4.5 h-4.5" />
                      Compliance Advisory Answer
                    </h3>
                    <div className="prose prose-invert text-zinc-200 text-sm whitespace-pre-wrap leading-relaxed">
                      {ragResponse.answer}
                    </div>
                  </div>

                  {/* Explainability Citations */}
                  <div className="glass-card p-6 space-y-4">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">Explainable AI Citations (No Hallucinations)</h3>
                    
                    <div className="space-y-4">
                      {ragResponse.citations.map((cite: any, idx: number) => (
                        <div key={idx} className="p-4 bg-zinc-950/40 border border-zinc-900 rounded-xl space-y-3">
                          <div className="flex justify-between items-center gap-3">
                            <span className="font-bold text-white text-xs">
                              {cite.document_title} (Clause {cite.clause_number})
                            </span>
                            <span className="px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-400 border border-cyan-900/30 text-[10px] font-bold shrink-0">
                              Confidence: {(cite.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          
                          <p className="text-zinc-400 text-xs italic bg-zinc-950 border border-zinc-900 p-3 rounded-lg whitespace-pre-line leading-relaxed">
                            "{cite.content}"
                          </p>

                          {cite.reasoning && (
                            <p className="text-zinc-500 text-[11px] font-semibold">
                              💡 Reasoning: {cite.reasoning}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* NOTIFICATIONS / AUDIT TRAIL SIDEBAR */}
      <aside className="w-80 border-l border-zinc-900/80 bg-zinc-950/10 shrink-0 p-6 space-y-6 overflow-y-auto">
        <div>
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-4">Compliance Feed Alerts</h3>
          <div className="space-y-3">
            {notifications.map((n) => (
              <div key={n.id} className="p-3.5 bg-zinc-900/40 border border-zinc-850 rounded-xl text-xs space-y-1 relative">
                <span className={`w-1.5 h-1.5 rounded-full absolute top-4 left-3 ${
                  n.type === 'alert' ? 'bg-red-500' : (n.type === 'success' ? 'bg-emerald-500' : 'bg-cyan-500')
                }`} />
                <div className="pl-4">
                  <h4 className="font-bold text-white">{n.title}</h4>
                  <p className="text-zinc-400 mt-1">{n.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-6 border-t border-zinc-900">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-4">System Diagnostic Status</h3>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Relational DB (SQLite/Postgres)</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> ONLINE
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Vector Indexer (Qdrant)</span>
              <span className="text-cyan-400 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full" /> LOCAL STATE
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Knowledge Graph (Neo4j)</span>
              <span className="text-cyan-400 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full" /> LOCAL STATE
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">AI Compilation Core</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> ACTIVE
              </span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
