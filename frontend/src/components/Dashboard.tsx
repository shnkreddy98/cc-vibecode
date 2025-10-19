import React, { useState, useEffect } from 'react';
import { Project } from '../types';
import { api } from '../services/api';
import '../styles/Dashboard.css';

interface DashboardProps {
  username: string;
  onLogout: () => void;
  onSelectProject: (project: Project) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ username, onLogout, onSelectProject }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProject, setNewProject] = useState({
    name: ''
  });

  useEffect(() => {
    loadProjects();
  }, [username]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await api.projects.list(username);
      setProjects(data);
    } catch (err) {
      setError('Failed to load projects. Using local storage fallback.');
      // Fallback to localStorage for demo purposes
      const stored = localStorage.getItem(`projects_${username}`);
      if (stored) {
        setProjects(JSON.parse(stored));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newProject.name) {
      setError('Please enter a project name');
      return;
    }

    try {
      setError('');
      const project: Project = {
        id: Date.now().toString(),
        name: newProject.name,
        username: username,
        previewUrl: 'http://localhost:3000',
        createdAt: new Date().toISOString()
      };

      // Try to create via API, fallback to localStorage
      try {
        const created = await api.projects.create(username, project);
        setProjects([...projects, created]);
      } catch {
        // Fallback to localStorage
        const updatedProjects = [...projects, project];
        setProjects(updatedProjects);
        localStorage.setItem(`projects_${username}`, JSON.stringify(updatedProjects));
      }

      setNewProject({ name: '' });
      setShowCreateModal(false);
    } catch (err) {
      setError('Failed to create project');
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!window.confirm('Are you sure you want to delete this project?')) {
      return;
    }

    try {
      await api.projects.delete(projectId);
      const updatedProjects = projects.filter(p => p.id !== projectId);
      setProjects(updatedProjects);
      localStorage.setItem(`projects_${username}`, JSON.stringify(updatedProjects));
    } catch {
      // Fallback to localStorage
      const updatedProjects = projects.filter(p => p.id !== projectId);
      setProjects(updatedProjects);
      localStorage.setItem(`projects_${username}`, JSON.stringify(updatedProjects));
    }
  };

  return (
    <div className="dashboard">
      <div className="navbar">
        <div className="navbar-brand">Airfold Apps</div>
        <div className="navbar-user">
          <span>Welcome, {username}</span>
          <button className="btn btn-secondary" onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>

      <div className="container">
        <div className="dashboard-header">
          <h2>My Projects</h2>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            Create Project
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {loading ? (
          <div className="loading">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="empty-state">
            <p>No projects yet. Create your first project to get started!</p>
          </div>
        ) : (
          <div className="projects-grid">
            {projects.map(project => (
              <div key={project.id} className="project-card">
                <div className="project-header">
                  <h3>{project.name}</h3>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDeleteProject(project.id)}
                  >
                    Delete
                  </button>
                </div>
                <div className="project-info">
                  <p><strong>GitHub:</strong> {project.username}/{project.name}</p>
                  <p><strong>Preview URL:</strong> {project.previewUrl}</p>
                  <p className="project-date">
                    Created: {new Date(project.createdAt).toLocaleDateString()}
                  </p>
                </div>
                <button
                  className="btn btn-primary btn-block"
                  onClick={() => onSelectProject(project)}
                >
                  Open Project
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">Create New Project</div>
            <form onSubmit={handleCreateProject}>
              <div className="form-group">
                <label>Project Name *</label>
                <input
                  type="text"
                  className="input"
                  placeholder="my-awesome-project"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ name: e.target.value })}
                  required
                  autoFocus
                />
                <p className="help-text">
                  Will create GitHub repo at: git@github.com:{username}/{newProject.name || 'project-name'}.git
                </p>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
