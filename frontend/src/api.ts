/**
 * ARHA API Client - Typed interface for all backend endpoints
 * Auto-generated from backend router contracts
 */

export interface Job {
  id: number;
  title: string;
  company: string;
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
}

export interface Resume {
  resume_id: number;
  filename: string;
  ats_score: number;
  word_count: number;
  ats_flags: string[];
  education_keywords: string[];
  experience_keywords: string[];
}

export interface MatchResult {
  overall_score: number;
  category: string;
  skill_match: number;
  experience_match: number;
  education_match: number;
  certification_match: number;
  project_relevance: number;
  location_match: number;
  matching_skills: string[];
  missing_skills: string[];
  explainability: {
    strengths: string[];
    gaps: string[];
    recommendation: string;
    reasoning: string;
  };
}

export interface Application {
  application_id: number;
  status: string;
  match_score: number;
  message: string;
}

export interface CompanyResearch {
  company_name: string;
  trust_score: number;
  trust_category: string;
  employee_sentiment: number;
  layoff_risk: string;
  growth_trend: string;
  funding_status: string;
  red_flags: string[];
  scam_reports: number;
  has_bond_agreement: boolean;
  has_fake_recruiters: boolean;
  has_unpaid_internships: boolean;
  headcount: number | null;
  summary: string;
  data_sources: string[];
}

export interface User {
  id: number;
  email: string;
  role: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// API Client methods
class ARHAApiClient {
  private baseURL: string;
  private token: string | null = null;

  constructor(baseURL: string = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000') {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('auth_token');
  }

  private async request<T>(method: string, path: string, options?: RequestInit): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options?.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseURL}${path}`, {
      ...options,
      method,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `Request failed: ${response.statusText}`);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth endpoints
  async register(email: string, password: string): Promise<User> {
    return this.request('POST', '/auth/register', {
      body: JSON.stringify({ email, password }),
    });
  }

  async login(email: string, password: string): Promise<Token> {
    const data = await this.request<Token>('POST', '/auth/token', {
      body: JSON.stringify({ email, password }),
    });
    this.token = data.access_token;
    localStorage.setItem('auth_token', data.access_token);
    return data;
  }

  async logout(): Promise<void> {
    await this.request('POST', '/auth/logout');
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  async getCurrentUser(): Promise<User> {
    return this.request('GET', '/auth/me');
  }

  // Jobs endpoints
  async searchJobs(q: string, location?: string, remote?: boolean, page?: number): Promise<{ jobs: Job[] }> {
    const params = new URLSearchParams({
      q,
      ...(location && { location }),
      ...(remote !== undefined && { remote: remote.toString() }),
      ...(page && { page: page.toString() }),
    });
    return this.request('GET', `/jobs/search?${params}`);
  }

  async getOpportunities(limit?: number, verified_only?: boolean): Promise<Job[]> {
    const params = new URLSearchParams({
      ...(limit && { limit: limit.toString() }),
      ...(verified_only && { verified_only: verified_only.toString() }),
    });
    return this.request('GET', `/jobs/opportunities?${params}`);
  }

  async matchResume(resume_text: string, job_description: string): Promise<MatchResult> {
    return this.request('POST', '/jobs/match', {
      body: JSON.stringify({ resume_text, job_description }),
    });
  }

  async applyForJob(
    job_id: string,
    job_title: string,
    company: string,
    resume_text: string,
    job_description: string
  ): Promise<Application> {
    return this.request('POST', '/jobs/apply', {
      body: JSON.stringify({
        job_id,
        job_title,
        company,
        resume_text,
        job_description,
      }),
    });
  }

  async getApplications(): Promise<Application[]> {
    return this.request('GET', '/jobs/applications');
  }

  async approveApplication(application_id: number): Promise<{ application_id: number; status: string }> {
    return this.request('POST', `/jobs/applications/${application_id}/approve`);
  }

  // Resume endpoints
  async uploadResume(file: File): Promise<Resume> {
    const formData = new FormData();
    formData.append('file', file);
    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const response = await fetch(`${this.baseURL}/resume/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!response.ok) {
      throw new Error('Failed to upload resume');
    }
    return response.json();
  }

  async getResume(resume_id: number): Promise<Resume & { content: string }> {
    return this.request('GET', `/resume/${resume_id}`);
  }

  async analyzeResume(resume_text: string): Promise<{ report: unknown }> {
    return this.request('POST', '/resume/analyze', {
      body: JSON.stringify({ resume_text }),
    });
  }

  async optimizeResume(resume_id: number, job_description: string, job_title?: string, company?: string) {
    return this.request('POST', '/resume/optimize', {
      body: JSON.stringify({
        resume_id,
        job_description,
        ...(job_title && { job_title }),
        ...(company && { company }),
      }),
    });
  }

  async getKeywordSuggestions(resume_text: string, job_description: string): Promise<{ keywords: string[] }> {
    return this.request('POST', '/resume/keywords', {
      body: JSON.stringify({ resume_text, job_description }),
    });
  }

  // Company endpoints
  async researchCompany(
    company_name: string,
    domain?: string,
    include_culture?: boolean,
    include_financials?: boolean
  ): Promise<CompanyResearch> {
    return this.request('POST', '/companies/research', {
      body: JSON.stringify({
        company_name,
        ...(domain && { domain }),
        include_culture: include_culture !== undefined ? include_culture : true,
        include_financials: include_financials !== undefined ? include_financials : false,
      }),
    });
  }

  async searchCompanies(q: string): Promise<CompanyResearch> {
    const params = new URLSearchParams({ q });
    return this.request('GET', `/companies/search?${params}`);
  }
}

export const apiClient = new ARHAApiClient();
