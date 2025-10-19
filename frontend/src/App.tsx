import React, { useState, useEffect } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import ProjectViewer from './components/ProjectViewer';
import { User, Project } from './types';
import './styles/global.css';

type View = 'login' | 'dashboard' | 'project';

function App() {
  const [currentView, setCurrentView] = useState<View>('login');
  const [user, setUser] = useState<User | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // Check if user is already logged in (from localStorage)
  useEffect(() => {
    const storedUser = localStorage.getItem('airfold_user');
    if (storedUser) {
      try {
        const userData = JSON.parse(storedUser);
        setUser(userData);
        setCurrentView('dashboard');
      } catch (e) {
        localStorage.removeItem('airfold_user');
      }
    }
  }, []);

  const handleLogin = (username: string) => {
    const userData: User = { username };
    setUser(userData);
    localStorage.setItem('airfold_user', JSON.stringify(userData));
    setCurrentView('dashboard');
  };

  const handleLogout = () => {
    setUser(null);
    setSelectedProject(null);
    localStorage.removeItem('airfold_user');
    setCurrentView('login');
  };

  const handleSelectProject = (project: Project) => {
    setSelectedProject(project);
    setCurrentView('project');
  };

  const handleBackToDashboard = () => {
    setSelectedProject(null);
    setCurrentView('dashboard');
  };

  return (
    <div className="App">
      {currentView === 'login' && (
        <Login onLogin={handleLogin} />
      )}

      {currentView === 'dashboard' && user && (
        <Dashboard
          username={user.username}
          onLogout={handleLogout}
          onSelectProject={handleSelectProject}
        />
      )}

      {currentView === 'project' && user && selectedProject && (
        <ProjectViewer
          project={selectedProject}
          username={user.username}
          onBack={handleBackToDashboard}
        />
      )}
    </div>
  );
}

export default App;
