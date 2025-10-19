import axios from 'axios';
import { ExecuteRequest, ExecuteResponse, Project, Feature } from '../types';

const API_BASE_URL = '/api';

// Create axios instance with extended timeout for long-running agent tasks
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minutes for agent execution
});

export const api = {
  // Execute endpoint - will be implemented as FastAPI endpoint later
  execute: async (request: ExecuteRequest): Promise<ExecuteResponse> => {
    const response = await axiosInstance.post<ExecuteResponse>('/execute', request);
    return response.data;
  },

  // Project management (uses default axios with standard timeout)
  projects: {
    list: async (username: string): Promise<Project[]> => {
      const response = await axios.get<Project[]>(`${API_BASE_URL}/projects`, {
        params: { username }
      });
      return response.data;
    },

    create: async (username: string, project: Omit<Project, 'id' | 'createdAt'>): Promise<Project> => {
      const response = await axios.post<Project>(`${API_BASE_URL}/projects`, {
        username,
        ...project
      });
      return response.data;
    },

    get: async (projectId: string): Promise<Project> => {
      const response = await axios.get<Project>(`${API_BASE_URL}/projects/${projectId}`);
      return response.data;
    },

    delete: async (projectId: string): Promise<void> => {
      await axios.delete(`${API_BASE_URL}/projects/${projectId}`);
    }
  },

  // Feature management (uses default axios with standard timeout)
  features: {
    list: async (projectId: string): Promise<Feature[]> => {
      const response = await axios.get<Feature[]>(`${API_BASE_URL}/features`, {
        params: { projectId }
      });
      return response.data;
    },

    create: async (feature: Omit<Feature, 'id' | 'createdAt' | 'status'>): Promise<Feature> => {
      const response = await axios.post<Feature>(`${API_BASE_URL}/features`, feature);
      return response.data;
    }
  }
};
