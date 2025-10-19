export interface User {
  username: string;
}

export interface Project {
  id: string;
  name: string;
  username: string;  // GitHub username
  createdAt: string;
  previewUrl?: string;
}

export interface Feature {
  id: string;
  projectId: string;
  title: string;
  prompt: string;
  branchName: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
}

export interface ExecuteRequest {
  url: string;
  projectName: string;
  branchName: string;
  dirPath: string;
  prompt: string;
  first: boolean;  // Required, not optional
}

export interface ExecuteResponse {
  success: boolean;
  message?: string;
  previewUrl?: string;
}
