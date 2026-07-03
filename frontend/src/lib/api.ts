const BASE_URL = "http://localhost:8000/api/v1";

export interface User {
  email: string;
  full_name: string;
  role: string;
  organization_id?: number;
}

export interface Document {
  id: number;
  title: string;
  filename: string;
  file_type: string;
  status: string;
  error_message?: string;
  created_at: string;
}

export interface Clause {
  id: number;
  clause_number: string;
  title?: string;
  content: string;
  section_path?: string;
}

export interface Obligation {
  id: number;
  clause_id?: number;
  document_id: number;
  title: string;
  description: string;
  applicability?: string;
  deadline?: string;
  frequency: string;
  penalties?: string;
  exceptions?: string;
  risk_level: string;
  status: string;
  created_at: string;
}

export interface Task {
  id: number;
  obligation_id: number;
  title: string;
  description?: string;
  assignee_id?: number;
  department_id: number;
  due_date?: string;
  status: string;
  evidence_required?: string;
  evidence_items?: any[];
  obligation?: Obligation;
}

export interface DashboardStats {
  compliance_score: number;
  pending_obligations: number;
  recent_circular_count: number;
  high_risk_pending: number;
  upcoming_deadlines: any[];
  department_performance: any[];
  risk_distribution: Record<string, number>;
  audit_readiness_score: number;
}

// ----------------------------------------------------
// Mock Data Store (for local failover)
// ----------------------------------------------------
let mockDocuments: Document[] = [
  { id: 1, title: "SEBI Master Circular for Mutual Funds 2024", filename: "sebi_mf_master_2024.pdf", file_type: "master_circular", status: "parsed", created_at: "2026-06-15T10:00:00" },
  { id: 2, title: "SEBI Cybersecurity Framework amendment", filename: "sebi_cyber_framework_2025.pdf", file_type: "circular", status: "parsed", created_at: "2026-06-20T14:30:00" }
];

let mockClauses: Clause[] = [
  { id: 1, clause_number: "1.1", title: "Apppointment of Chief Information Security Officer (CISO)", content: "All mutual funds and portfolio managers shall designate a qualified Chief Information Security Officer (CISO) who shall be responsible for cybersecurity posture and data privacy reporting directly to the Board of Directors.", section_path: "Cybersecurity > Governance" },
  { id: 2, clause_number: "2.3", title: "Vulnerability Assessments (VAPT)", content: "Intermediaries shall perform Vulnerability Assessment and Penetration Testing (VAPT) at least once in a financial year by an auditor certified by CERT-In. The reports must be submitted within 30 days of completion.", section_path: "Cybersecurity > Operations" }
];

let mockObligations: Obligation[] = [
  { id: 1, clause_id: 1, document_id: 2, title: "Designate CISO Role", description: "All mutual funds and portfolio managers shall designate a CISO reporting directly to the Board.", applicability: "Mutual Funds, Portfolio Managers", deadline: "Within 90 days from circular date", frequency: "One-off", penalties: "Registration suspension or fine up to 5,000 INR per day of delay", exceptions: "None", risk_level: "High", status: "active", created_at: "2026-06-20" },
  { id: 2, clause_id: 2, document_id: 2, title: "Conduct Annual VAPT Audits", description: "Intermediaries must perform VAPT audit annually by CERT-In auditor and upload reports within 30 days.", applicability: "All Intermediaries", deadline: "Annually (Before March 31)", frequency: "Annually", penalties: "Audit warnings or financial restrictions", exceptions: "Intermediaries with less than 50 clients", risk_level: "High", status: "active", created_at: "2026-06-20" }
];

let mockTasks: Task[] = [
  { id: 1, obligation_id: 1, title: "Board Resolution for CISO Appointee", description: "Draft board resolution, identify candidate, and complete designation details.", department_id: 1, due_date: "2026-09-20T00:00:00", status: "completed", evidence_required: "Signed Board Resolution PDF", evidence_items: [{ filename: "ciso_resolution_signed.pdf", verification_status: "approved" }], obligation: mockObligations[0] },
  { id: 2, obligation_id: 2, title: "Schedule VAPT Audit Vendor", description: "Procure services of a CERT-In certified auditor, schedule audits, and collect draft reports.", department_id: 2, due_date: "2026-12-15T00:00:00", status: "pending", evidence_required: "VAPT Audit Agreement & Work Order", evidence_items: [], obligation: mockObligations[1] },
  { id: 3, obligation_id: 2, title: "Submit VAPT Audit Report to SEBI Portal", description: "Review final reports and upload to SEBI compliance system.", department_id: 1, due_date: "2026-03-31T00:00:00", status: "pending", evidence_required: "SEBI Portal Upload confirmation sheet", evidence_items: [], obligation: mockObligations[1] }
];

let mockGraph = {
  nodes: [
    { id: "doc_1", label: "Regulation", properties: { title: "SEBI Cybersecurity framework", date: "2026-06-20" } },
    { id: "clause_1", label: "Clause", properties: { clause_number: "1.1", title: "Apppointment of CISO", content: "Designate CISO" } },
    { id: "obligation_1", label: "Obligation", properties: { title: "Designate CISO Role", risk_level: "High", frequency: "One-off" } },
    { id: "dept_1", label: "Department", properties: { name: "Compliance" } },
    { id: "dept_2", label: "Department", properties: { name: "Operations" } }
  ],
  edges: [
    { source: "doc_1", target: "clause_1", type: "HAS_CLAUSE" },
    { source: "clause_1", target: "obligation_1", type: "HAS_OBLIGATION" },
    { source: "obligation_1", target: "dept_1", type: "ASSIGNED_TO" }
  ]
};

// Helper fetch client with mock fallbacks
async function request(path: string, options: RequestInit = {}): Promise<any> {
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;
  const headers = {
    ...options.headers,
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };

  try {
    const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
    if (!res.ok) {
      if (res.status === 401 && typeof window !== 'undefined') {
        localStorage.removeItem("token");
      }
      throw new Error(`Request failed with status ${res.status}`);
    }
    return await res.json();
  } catch (error) {
    console.warn(`API network error on ${path}, triggering mock fallback. Error:`, error);
    return getMockFallback(path, options);
  }
}

function getMockFallback(path: string, options: RequestInit): any {
  if (path.startsWith("/auth/login")) {
    const body = JSON.parse(options.body as string);
    if (body.email === "compliance@sebicopilot.com" && body.password === "password") {
      return {
        access_token: "mock-jwt-token-xyz",
        token_type: "bearer",
        user: { email: "compliance@sebicopilot.com", full_name: "Compliance Officer Primary", role: "Compliance Officer" }
      };
    }
    throw new Error("Invalid mock credentials");
  }
  
  if (path.startsWith("/auth/me")) {
    return { email: "compliance@sebicopilot.com", full_name: "Compliance Officer Primary", role: "Compliance Officer" };
  }

  if (path.startsWith("/dashboard/stats")) {
    return {
      compliance_score: 33.3,
      pending_obligations: 2,
      recent_circular_count: 2,
      high_risk_pending: 1,
      upcoming_deadlines: [
        { task_id: 2, title: "Schedule VAPT Audit Vendor", due_date: "2026-12-15", risk_level: "High", department: "Operations" },
        { task_id: 3, title: "Submit VAPT Audit Report to SEBI Portal", due_date: "2026-03-31", risk_level: "High", department: "Compliance" }
      ],
      department_performance: [
        { name: "Compliance", compliance_rate: 50.0, pending_count: 1 },
        { name: "Operations", compliance_rate: 0.0, pending_count: 1 }
      ],
      risk_distribution: { "High": 2, "Medium": 0, "Low": 0 },
      audit_readiness_score: 33.3
    };
  }

  if (path.startsWith("/dashboard/gaps")) {
    return {
      compliance_score: 33.3,
      total_obligations: 2,
      compliant_count: 1,
      gap_count: 2,
      gaps: [
        { obligation_id: 2, obligation_title: "Conduct Annual VAPT Audits", risk_level: "High", task_id: 2, task_title: "Schedule VAPT Audit Vendor", status: "missing_evidence", message: "Compliance evidence missing. Assignee needs to upload: 'VAPT Audit Agreement & Work Order'." },
        { obligation_id: 2, obligation_title: "Conduct Annual VAPT Audits", risk_level: "High", task_id: 3, task_title: "Submit VAPT Audit Report to SEBI Portal", status: "missing_evidence", message: "Compliance evidence missing. Assignee needs to upload: 'SEBI Portal Upload confirmation sheet'." }
      ]
    };
  }

  if (path.startsWith("/dashboard/graph")) {
    return mockGraph;
  }

  if (path.startsWith("/documents")) {
    if (options.method === "POST" && path.includes("upload")) {
      // Simulate file upload
      const newDoc: Document = {
        id: mockDocuments.length + 1,
        title: "Mock Document " + mockDocuments.length,
        filename: "uploaded_doc.pdf",
        file_type: "circular",
        status: "parsed",
        created_at: new Date().toISOString()
      };
      mockDocuments.push(newDoc);
      return newDoc;
    }
    
    if (path.includes("/diff")) {
      return {
        base_doc_title: "SEBI circular version A",
        compare_doc_title: "SEBI circular version B",
        diffs: [
          { clause_number: "1.1", base_content: "Audit report should be filed in 45 days.", compare_content: "Audit report should be filed in 30 days.", change_type: "modified", timeline_changed: true, penalty_changed: false },
          { clause_number: "1.2", base_content: "Penalty is Rs. 1000", compare_content: null, change_type: "deleted" },
          { clause_number: "1.3", base_content: null, compare_content: "Intermediaries must install firewall configurations.", change_type: "added" }
        ],
        impact_summary: "### Impact Analysis Summary\n- **Timeline reduced**: Audit filings must be completed in **30 days** instead of 45.\n- **Deleted Clause 1.2**: Financial penalty rules removed.\n- **Security obligation added**: Intermediaries must configure firewalls."
      };
    }

    if (path.includes("/rag")) {
      const body = JSON.parse(options.body as string);
      return {
        answer: `### Compliance Advisory for: "${body.query}"\n\nUnder SEBI guidelines, intermediaries are required to execute annual penetration testing (VAPT) via CERT-In certified audit vendors. Final reports must be verified and uploaded within 30 days of receipt.\n\n*Action Checklist:*\n1. Retain CERT-In auditor.\n2. Submit report through the designated portal.`,
        citations: [
          { document_id: 2, document_title: "SEBI Cybersecurity Framework amendment", clause_number: "2.3", content: "Intermediaries shall perform Vulnerability Assessment and Penetration Testing (VAPT) at least once in a financial year...", confidence: 0.94, reasoning: "Direct keyword and conceptual overlap for VAPT search." }
        ],
        confidence_score: 0.94
      };
    }

    return mockDocuments;
  }

  if (path.startsWith("/workflows")) {
    if (path.includes("/tasks")) {
      const parts = path.split("/");
      if (parts.length > 3) {
        // e.g. /workflows/tasks/2/evidence
        const taskId = parseInt(parts[3]);
        if (parts.includes("evidence")) {
          const task = mockTasks.find(t => t.id === taskId);
          if (task) {
            task.status = "in_progress";
            const newEvidence = { id: Date.now(), task_id: taskId, filename: "evidence.pdf", file_path: "/mock/path", uploaded_by: 1, description: "", verification_status: "pending", created_at: new Date().toISOString() };
            task.evidence_items?.push(newEvidence);
            return newEvidence;
          }
        }
        if (parts.includes("verify")) {
          // get the value from body (query params or form)
          const task = mockTasks.find(t => t.id === taskId);
          if (task) {
            task.status = "completed";
            if (task.evidence_items && task.evidence_items.length > 0) {
              task.evidence_items[task.evidence_items.length - 1].verification_status = "approved";
            }
            return task;
          }
        }
        return mockTasks.find(t => t.id === taskId);
      }
      return mockTasks;
    }
    return [{ id: 1, obligation_id: 1, name: "CISO Onboarding Workflow", status: "active", step_data: null, current_step: 1 }];
  }

  return {};
}

// Exportable API actions
export const api = {
  login: (credentials: UserLogin) => request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials)
  }),
  
  getMe: () => request("/auth/me"),
  
  getDashboardStats: () => request("/dashboard/stats"),
  
  getGaps: () => request("/dashboard/gaps"),
  
  getGraph: () => request("/dashboard/graph"),

  getDocuments: () => request("/documents"),

  uploadDocument: async (formData: FormData) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;
    try {
      const res = await fetch(`${BASE_URL}/documents/upload`, {
        method: "POST",
        headers: token ? { "Authorization": `Bearer ${token}` } : {},
        body: formData
      });
      if (!res.ok) throw new Error("Upload failed");
      return await res.json();
    } catch (e) {
      console.warn("Upload network error, triggering mock upload fallback.", e);
      return getMockFallback("/documents/upload", { method: "POST" });
    }
  },

  getClauses: (docId: number) => request(`/documents/${docId}/clauses`),

  getObligations: (docId: number) => request(`/documents/${docId}/obligations`),

  getDiff: (payload: DiffComparisonRequest) => request("/documents/diff", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }),

  ragQuery: (query: string) => request("/documents/rag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query })
  }),

  getTasks: () => request("/workflows/tasks"),

  uploadEvidence: async (taskId: number, file: File, description?: string) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;
    const formData = new FormData();
    formData.append("file", file);
    if (description) formData.append("description", description);

    try {
      const res = await fetch(`${BASE_URL}/workflows/tasks/${taskId}/evidence`, {
        method: "POST",
        headers: token ? { "Authorization": `Bearer ${token}` } : {},
        body: formData
      });
      if (!res.ok) throw new Error("Evidence upload failed");
      return await res.json();
    } catch (e) {
      console.warn("Evidence upload network error, triggering mock fallback.", e);
      return getMockFallback(`/workflows/tasks/${taskId}/evidence`, { method: "POST" });
    }
  },

  verifyEvidence: async (taskId: number, action: "approve" | "reject", comment?: string) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;
    const formData = new FormData();
    formData.append("action", action);
    if (comment) formData.append("comment", comment);

    try {
      const res = await fetch(`${BASE_URL}/workflows/tasks/${taskId}/verify`, {
        method: "POST",
        headers: token ? { "Authorization": `Bearer ${token}` } : {},
        body: formData
      });
      if (!res.ok) throw new Error("Verification failed");
      return await res.json();
    } catch (e) {
      console.warn("Verification network error, triggering mock fallback.", e);
      return getMockFallback(`/workflows/tasks/${taskId}/verify`, { method: "POST", body: JSON.stringify({ action, comment }) });
    }
  },

  exportReportUrl: () => {
    return `${BASE_URL}/workflows/export-report`;
  }
};
