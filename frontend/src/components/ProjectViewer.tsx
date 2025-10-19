import React, { useState, useEffect, useRef } from 'react';
import { Project, Feature } from '../types';
import { api } from '../services/api';
import PromptModal from './PromptModal';
import '../styles/ProjectViewer.css';

interface ProjectViewerProps {
  project: Project;
  username: string;
  onBack: () => void;
}

const ProjectViewer: React.FC<ProjectViewerProps> = ({ project, username, onBack }) => {
  const [features, setFeatures] = useState<Feature[]>([]);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [clickPosition, setClickPosition] = useState({ x: 0, y: 0 });
  const [processing, setProcessing] = useState(false);
  const [currentFeature, setCurrentFeature] = useState<Feature | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadFeatures();
  }, [project.id]);

  const loadFeatures = async () => {
    try {
      const data = await api.features.list(project.id);
      setFeatures(data);
    } catch {
      // Fallback to localStorage
      const stored = localStorage.getItem(`features_${project.id}`);
      if (stored) {
        setFeatures(JSON.parse(stored));
      }
    }
  };

  const handleIframeClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (processing) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setClickPosition({ x, y });
    setShowPromptModal(true);
  };

  const handleSubmitPrompt = async (title: string, prompt: string) => {
    setShowPromptModal(false);
    setProcessing(true);

    // First feature uses project name as branch, subsequent use feature title
    const isFirstFeature = features.length === 0;
    const branchName = isFirstFeature
      ? project.name.toLowerCase().replace(/\s+/g, '_')
      : `${title.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}`;

    // Always use tmp - gets deleted and recreated each time anyway
    const dirPath = 'tmp';

    const feature: Feature = {
      id: Date.now().toString(),
      projectId: project.id,
      title,
      prompt,
      branchName,
      status: 'processing',
      createdAt: new Date().toISOString()
    };

    // Add feature to list
    const updatedFeatures = [...features, feature];
    setFeatures(updatedFeatures);
    setCurrentFeature(feature);
    localStorage.setItem(`features_${project.id}`, JSON.stringify(updatedFeatures));

    try {
      // Construct git URL and project name
      const gitUrl = `git@github.com:${project.username}/${project.name}.git`;

      // Call execute endpoint
      const result = await api.execute({
        url: gitUrl,
        projectName: project.name,  // Use project name for Neon
        branchName,
        dirPath,
        prompt,
        first: features.length === 0 // first is true if this is the first feature
      });

      // Update feature status
      feature.status = result.success ? 'completed' : 'failed';
      const finalFeatures = updatedFeatures.map(f =>
        f.id === feature.id ? feature : f
      );
      setFeatures(finalFeatures);
      localStorage.setItem(`features_${project.id}`, JSON.stringify(finalFeatures));

      // Reload iframe to show updated content
      if (result.success) {
        setIframeKey(prev => prev + 1);
      }
    } catch (error) {
      console.error('Execute error:', error);
      feature.status = 'failed';
      const finalFeatures = updatedFeatures.map(f =>
        f.id === feature.id ? feature : f
      );
      setFeatures(finalFeatures);
      localStorage.setItem(`features_${project.id}`, JSON.stringify(finalFeatures));
    } finally {
      setProcessing(false);
      setCurrentFeature(null);
    }
  };

  const getPreviewUrl = () => {
    // Use the project's preview URL or a default local server
    return project.previewUrl || 'http://localhost:3000';
  };

  return (
    <div className="project-viewer">
      <div className="navbar">
        <div className="navbar-brand">
          <button className="btn btn-secondary" onClick={onBack}>
            Back
          </button>
          <span className="project-name">{project.name}</span>
        </div>
        <div className="navbar-user">
          <span>{username}</span>
        </div>
      </div>

      <div className="viewer-container">
        <div className="sidebar">
          <div className="sidebar-header">
            <h3>Features</h3>
            {processing && <div className="processing-indicator">Processing...</div>}
          </div>

          <div className="features-list">
            {features.length === 0 ? (
              <p className="empty-features">
                Click anywhere on the preview to create your first feature
              </p>
            ) : (
              features.map(feature => (
                <div
                  key={feature.id}
                  className={`feature-item ${feature.status} ${
                    currentFeature?.id === feature.id ? 'active' : ''
                  }`}
                >
                  <div className="feature-title">{feature.title}</div>
                  <div className="feature-meta">
                    <span className={`status-badge ${feature.status}`}>
                      {feature.status}
                    </span>
                    <span className="feature-date">
                      {new Date(feature.createdAt).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="feature-prompt">{feature.prompt}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="preview-area">
          <div className="preview-header">
            <h3>Live Preview</h3>
            <div className="preview-actions">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setIframeKey(prev => prev + 1)}
                disabled={processing}
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="iframe-container">
            {processing && (
              <div className="iframe-overlay processing">
                <div className="overlay-message">
                  <div className="spinner"></div>
                  <p>Processing feature: {currentFeature?.title}</p>
                  <p className="overlay-subtext">This may take a few moments...</p>
                </div>
              </div>
            )}

            <div
              ref={overlayRef}
              className="iframe-click-overlay"
              onClick={handleIframeClick}
              style={{ display: processing ? 'none' : 'block' }}
            />

            <iframe
              ref={iframeRef}
              key={iframeKey}
              src={getPreviewUrl()}
              title="Project Preview"
              className="preview-iframe"
              sandbox="allow-scripts allow-same-origin allow-forms"
            />
          </div>

          <div className="preview-footer">
            <p className="hint">
              Click anywhere on the preview to add a new feature
            </p>
          </div>
        </div>
      </div>

      {showPromptModal && (
        <PromptModal
          onSubmit={handleSubmitPrompt}
          onClose={() => setShowPromptModal(false)}
        />
      )}
    </div>
  );
};

export default ProjectViewer;
