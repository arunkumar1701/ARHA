import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  BadgeCheck,
  Bot,
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  History,
  Home,
  Layers3,
  Rocket,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  UserCircle
} from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

type Job = {
  id: number;
  company: string;
  role: string;
  location: string;
  employment_type: string;
  requirements: string;
  salary: string | null;
  apply_url: string;
  source_platform: string;
  posted_date: string;
  verification_timestamp: string;
  verification_status: string;
  risk_level: string;
  company_assessment: string;
  recommendation: string;
  approval_required: string;
};

type Optimization = {
  optimization_id: number;
  status: string;
  report: {
    company: string;
    role: string;
    role_focus: string;
    company_style: string;
    current_resume_issues: string[];
    suggested_changes: Array<{
      id: string;
      category: string;
      current_content: string;
      suggested_content: string;
      estimated_impact: string;
    }>;
    ats_score_before: number;
    ats_score_after: number;
    current_match_score: number;
    potential_match_score: number;
    expected_ats_improvement: number;
    expected_match_score_improvement: number;
    estimated_impact: string;
    missing_skills_remaining: string[];
    readiness_notes: string[];
  };
};

type ResumeVersion = {
  id: number;
  version_name: string;
  job_id: number | null;
  change_log: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
};

function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<Job | null>(null);
  const [resumeReport, setResumeReport] = useState<any>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [versions, setVersions] = useState<ResumeVersion[]>([]);
  const [optimization, setOptimization] = useState<Optimization | null>(null);
  const [readiness, setReadiness] = useState<any>(null);
  const [finalReport, setFinalReport] = useState<any>(null);
  const [message, setMessage] = useState('Career strategist active. Upload a resume, discover jobs, then optimize before applying.');
  const [busy, setBusy] = useState(false);

  const selectedJob = selected || jobs[0] || null;
  const matchLabel = useMemo(() => {
    if (optimization) return `${optimization.report.potential_match_score}% Potential`;
    if (selectedJob?.verification_status === 'verified') return 'Verified';
    return 'Needs review';
  }, [optimization, selectedJob]);

  async function request(path: string, options?: RequestInit) {
    const response = await fetch(`${API}${path}`, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'ARHA request failed.');
    return data;
  }

  async function refresh() {
    const [jobData, auditData, versionData] = await Promise.all([
      request('/jobs').catch(() => ({ jobs: [] })),
      request('/audit-log').catch(() => ({ events: [] })),
      request('/resume/versions').catch(() => ({ versions: [] }))
    ]);
    setJobs(jobData.jobs || []);
    setAudit(auditData.events || []);
    setVersions(versionData.versions || []);
    if (!selected && jobData.jobs?.length) setSelected(jobData.jobs[0]);
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(error.message));
  }, []);

  async function runAction(label: string, action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : `${label} failed.`);
    } finally {
      setBusy(false);
    }
  }

  async function uploadResume(file: File) {
    await runAction('Resume upload', async () => {
      const form = new FormData();
      form.append('file', file);
      const data = await request('/resume/upload', { method: 'POST', body: form });
      setResumeReport(data.report);
      setMessage('Resume analyzed locally, encrypted, and versioned as Resume_v1_Original.');
      await refresh();
    });
  }

  async function runDiscovery() {
    await runAction('Discovery', async () => {
      const data = await request('/jobs/search/local', { method: 'POST' });
      setMessage(data.note);
      await refresh();
    });
  }

  async function runScore() {
    if (!selectedJob) return;
    await runAction('Scoring', async () => {
      const data = await request(`/jobs/${selectedJob.id}/score`, { method: 'POST' });
      setMessage(`Current match score: ${data.overall_score}% (${data.category}).`);
      await refresh();
    });
  }

  async function runOptimization(jobOverride?: Job) {
    const jobToOptimize = jobOverride || selectedJob;
    if (!jobToOptimize) return;
    await runAction('Resume optimization', async () => {
      const data = await request(`/jobs/${jobToOptimize.id}/resume-optimization`, { method: 'POST' });
      setOptimization(data);
      setFinalReport(null);
      setReadiness(null);
      setMessage('Resume strategist generated changes. Review current content, suggested content, and expected impact before approval.');
      await refresh();
    });
  }

  async function decideOptimization(action: 'approve_all' | 'reject' | 'request_alternative') {
    if (!optimization) return;
    const approvalText =
      action === 'approve_all'
        ? 'Do you approve these resume changes? This creates a new encrypted resume version and does not overwrite the original.'
        : action === 'reject'
          ? 'Reject these resume changes? No resume version will be created.'
          : 'Request alternative suggestions? ARHA will keep the original resume unchanged.';
    if (!window.confirm(approvalText)) return;

    await runAction('Optimization decision', async () => {
      const data = await request(`/resume/optimizations/${optimization.optimization_id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, details: { source: 'frontend_resume_strategist' } })
      });
      setOptimization(data);
      setMessage(`Resume optimization status: ${data.status}.`);
      await refresh();
    });
  }

  async function restoreVersion(versionId: number) {
    await runAction('Version restore', async () => {
      await request(`/resume/versions/${versionId}/restore`, { method: 'POST' });
      setMessage('Resume version restored. Future packages will use the active approved workflow where required.');
      await refresh();
    });
  }

  async function checkReadiness() {
    if (!selectedJob) return;
    await runAction('Readiness check', async () => {
      const data = await request(`/jobs/${selectedJob.id}/application-readiness`);
      setReadiness(data);
      setMessage(data.message);
      await refresh();
    });
  }

  async function createPackage() {
    if (!selectedJob) return;
    const approved = window.confirm(
      `Do you approve this action?\n\nAction: prepare a local application package draft.\nCompany: ${selectedJob.company}\nRole: ${selectedJob.role}\nData used: approved optimized resume version and verified job details.\nNo submission, email, upload, referral request, or external sharing will occur.`
    );
    if (!approved) {
      setMessage('Final approval declined. No application package was prepared.');
      return;
    }
    await runAction('Application package', async () => {
      await request('/approvals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_type: 'application_package',
          target_type: 'job',
          target_id: selectedJob.id,
          approved: true,
          details: { scope: 'prepare local draft only; no submission or external sharing approved' }
        })
      });
      const data = await request(`/jobs/${selectedJob.id}/application-package`, { method: 'POST' });
      setMessage(`Application package ${data.package_id} prepared with ${data.payload.resume_version_name}. Submission still requires separate approval.`);
      await refresh();
    });
  }

  async function loadFinalReport() {
    if (!selectedJob) return;
    await runAction('Final report', async () => {
      const data = await request(`/jobs/${selectedJob.id}/final-recommendation`);
      setFinalReport(data);
      setReadiness(data.readiness);
      setMessage(data.approval_question);
    });
  }

  return (
    <main className="app-shell">
      <header className="topbar glass-panel">
        <div className="brand">
          <span className="brand-mark"><Activity size={18} /></span>
          <strong>ARHA</strong>
        </div>
        <button className="icon-button" title="Search onClick={() => alert('Search feature coming soon!')}"><Search size={20} /></button>
            <div className="profile-dot" onClick={() => alert('Profile coming soon!')} style={{cursor: 'pointer'}}><UserCircle size={26} /></div>          "><UserCircle size={26} /></div>
      </header>

      <section className="hero">
        <p>CAREER STRATEGIST ACTIVE</p>
        <h1>Your next move is waiting.</h1>
        <div className="command glass-panel">
          <Sparkles size={18} />
          <span>{message}</span>
        </div>
      </section>

      <section className="actions glass-panel">
        <button onClick={runDiscovery} disabled={busy}><BriefcaseBusiness size={17} /> Discover</button>
        <label className="upload-action">
          <Upload size={17} /> Resume PDF
          <input type="file" accept="application/pdf" onChange={(event) => event.target.files?.[0] && uploadResume(event.target.files[0])} />
        </label>
        <button onClick={runScore} disabled={!selectedJob || busy}><Activity size={17} /> Score</button>
        <button onClick={() => runOptimization()} disabled={!selectedJob || busy}><Bot size={17} /> Optimize</button>
      </section>

      <section className="section-head">
        <h2>Active Applications</h2>
        <span>View Board</span>
      </section>
      <div className="kanban">
        {['Resume Analysis', 'Optimization', 'Readiness'].map((item, index) => (
                <button onClick={() => alert('Board view coming soon!')} style={{background: 'none', border: 'none', cursor: 'pointer', color: 'inherit'}}>View Board</button>            <div className="mini-top">
              <span className="mini-icon">{index === 0 ? <FileText size={16} /> : index === 1 ? <Sparkles size={16} /> : <ClipboardCheck size={16} />}</span>
              <span className={index === 1 && optimization ? 'pill lime' : 'pill'}>{index === 1 && optimization ? optimization.status : 'Pending'}</span>
            </div>
            <strong>{item}</strong>
            <small>{selectedJob ? `${selectedJob.company} / ${selectedJob.role}` : 'No job selected'}</small>
          </article>
        ))}
      </div>

      <section className="section-head">
        <h2>Recommended For You</h2>
        <span>{jobs.length} stored</span>
      </section>
      <section className="job-feed">
        {jobs.length === 0 && <div className="empty-state glass-card">No opportunities stored yet. Run public discovery to fetch verified public sources.</div>}
        {jobs.map((job) => (
          <article className={selectedJob?.id === job.id ? 'job-card glass-card selected' : 'job-card glass-card'} key={job.id} onClick={() => setSelected(job)}>
            <div className="match-pill"><Sparkles size={14} /> {selectedJob?.id === job.id ? matchLabel : job.verification_status}</div>
            <div className="job-main">
              <div className="company-icon"><Layers3 size={25} /></div>
              <div>
                <h3>{job.role}</h3>
                <p>{job.company} - {job.location}</p>
              </div>
            </div>
            <div className="tags">
              <span>{job.employment_type}</span>
              <span>{job.posted_date}</span>
              <span>{job.risk_level}</span>
            </div>
            <div className="agent-insight">
              <div><Bot size={18} /> AGENT INSIGHT</div>
              <p>{job.company_assessment || 'Company data is insufficient. ARHA will not guess.'}</p>
            </div>
            <div className="card-actions">
              <button onClick={(event) => { event.stopPropagation(); setSelected(job); runOptimization(job); }}>Resume Strategist</button>
              <a href={job.apply_url} target="_blank" onClick={(event) => event.stopPropagation()}>Source</a>
            </div>
          </article>
        ))}
      </section>

      <section className="workspace">
        <StrategistPanel optimization={optimization} onApprove={() => decideOptimization('approve_all')} onReject={() => decideOptimization('reject')} onAlternative={() => decideOptimization('request_alternative')} />
        <ReadinessPanel readiness={readiness} finalReport={finalReport} onReadiness={checkReadiness} onFinal={loadFinalReport} onPackage={createPackage} selectedJob={selectedJob} />
        <VersionsPanel versions={versions} onRestore={restoreVersion} />
        <ResumePanel report={resumeReport} audit={audit} />
        {selectedJob && <OpportunityReport job={selectedJob} />}
      </section>

      <nav className="bottom-nav glass-panel">
        <span className="active"><Home size={20} /> Home</span>
        <span><Bot size={20} /> Agents</span>
        <span><BriefcaseBusiness size={20} /> Apps</span>
        <span><UserCircle size={20} /> Profile</span>
      </nav>
    </main>
  );
}

function StrategistPanel({ optimization, onApprove, onReject, onAlternative }: { optimization: Optimization | null; onApprove: () => void; onReject: () => void; onAlternative: () => void }) {
  return (
    <section className="glass-panel detail-panel">
      <div className="panel-title"><Sparkles size={18} /> Intelligent Resume Strategist</div>
      {!optimization ? (
        <p className="muted">Run Optimize on a selected job to compare resume, job description, company requirements, ATS keywords, and role strategy.</p>
      ) : (
        <>
          <div className="score-grid">
            <Metric label="Current Match" value={`${optimization.report.current_match_score}%`} />
            <Metric label="Potential Match" value={`${optimization.report.potential_match_score}%`} />
            <Metric label="ATS Before" value={`${optimization.report.ats_score_before}%`} />
            <Metric label="ATS After" value={`${optimization.report.ats_score_after}%`} />
          </div>
          <div className="strategy-line">
            <span>Role focus: {optimization.report.role_focus}</span>
            <span>Company style: {optimization.report.company_style}</span>
            <span>Impact: {optimization.report.estimated_impact}</span>
          </div>
          <div className="changes">
            {optimization.report.suggested_changes.map((change) => (
              <article key={change.id}>
                <strong>{change.category}</strong>
                <p><b>Current:</b> {change.current_content}</p>
                <p><b>Suggested:</b> {change.suggested_content}</p>
                <small>{change.estimated_impact}</small>
              </article>
            ))}
          </div>
          <div className="button-row">
            <button onClick={onApprove}><CheckCircle2 size={16} /> Approve All</button>
            <button onClick={onAlternative}>Request Alternative</button>
            <button className="danger" onClick={onReject}>Reject</button>
          </div>
        </>
      )}
    </section>
  );
}

function ReadinessPanel({ readiness, finalReport, onReadiness, onFinal, onPackage, selectedJob }: { readiness: any; finalReport: any; onReadiness: () => void; onFinal: () => void; onPackage: () => void; selectedJob: Job | null }) {
  const checks = readiness?.checks || {};
  return (
    <section className="glass-panel detail-panel">
      <div className="panel-title"><ShieldCheck size={18} /> Application Readiness</div>
      <div className="check-list">
        {['resume_optimized', 'missing_keywords_addressed', 'ats_score_acceptable', 'skill_gaps_identified', 'company_verified', 'job_still_active'].map((key) => (
          <div key={key} className={checks[key] ? 'check good' : 'check'}>
            <BadgeCheck size={16} />
            <span>{key.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
      {finalReport && (
        <div className="final-report">
          <strong>Final Recommendation</strong>
          <p>Current match: {finalReport.current_match_score}%</p>
          <p>Potential match: {finalReport.potential_match_score_after_resume_changes}%</p>
          <p>ATS: {finalReport.ats_score_before}% to {finalReport.ats_score_after}%</p>
          <p>Recommendation: {finalReport.recommendation}</p>
        </div>
      )}
      <div className="button-row">
        <button onClick={onReadiness} disabled={!selectedJob}>Check</button>
        <button onClick={onFinal} disabled={!selectedJob}>Final Report</button>
        <button onClick={onPackage} disabled={!selectedJob}><Rocket size={16} /> Prepare Package</button>
      </div>
    </section>
  );
}

function VersionsPanel({ versions, onRestore }: { versions: ResumeVersion[]; onRestore: (id: number) => void }) {
  return (
    <section className="glass-panel detail-panel">
      <div className="panel-title"><History size={18} /> Resume Versions</div>
      <div className="version-list">
        {versions.length === 0 && <p className="muted">No resume versions yet. Upload a resume to create Resume_v1_Original.</p>}
        {versions.map((version) => (
          <article key={version.id} className={version.is_active ? 'version active-version' : 'version'}>
            <div>
              <strong>{version.version_name}</strong>
              <small>{version.created_at}</small>
            </div>
            <button onClick={() => onRestore(version.id)} disabled={version.is_active}>{version.is_active ? 'Active' : 'Restore'}</button>
          </article>
        ))}
      </div>
    </section>
  );
}

function ResumePanel({ report, audit }: { report: any; audit: any[] }) {
  return (
    <section className="glass-panel detail-panel">
      <div className="panel-title"><FileText size={18} /> Resume Intelligence</div>
      {report ? (
        <div className="score-grid compact">
          <Metric label="ATS Score" value={`${report.ats_score}%`} />
          <Metric label="Skills" value={`${report.skills?.length || 0}`} />
        </div>
      ) : (
        <p className="muted">Upload a PDF resume for encrypted local analysis.</p>
      )}
      <div className="audit">
        {audit.slice(0, 5).map((event) => <p key={event.id}>{event.created_at} / {event.event_type}</p>)}
      </div>
    </section>
  );
}

function OpportunityReport({ job }: { job: Job }) {
  return (
    <section className="glass-panel detail-panel wide">
      <div className="panel-title"><ClipboardCheck size={18} /> Opportunity Report</div>
      <dl className="report">
        <dt>Company:</dt><dd>{job.company}</dd>
        <dt>Role:</dt><dd>{job.role}</dd>
        <dt>Location:</dt><dd>{job.location}</dd>
        <dt>Employment Type:</dt><dd>{job.employment_type}</dd>
        <dt>Apply URL:</dt><dd><a href={job.apply_url} target="_blank">{job.apply_url}</a></dd>
        <dt>Source Platform:</dt><dd>{job.source_platform}</dd>
        <dt>Posted Date:</dt><dd>{job.posted_date}</dd>
        <dt>Company Assessment:</dt><dd>{job.company_assessment}</dd>
        <dt>Risk Level:</dt><dd>{job.risk_level}</dd>
        <dt>Recommendation:</dt><dd>{job.recommendation}</dd>
        <dt>Approval Required:</dt><dd>{job.approval_required}</dd>
        <dt>Evidence Sources:</dt><dd>{job.apply_url}</dd>
        <dt>Verification Timestamp:</dt><dd>{job.verification_timestamp || 'Unavailable'}</dd>
      </dl>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
