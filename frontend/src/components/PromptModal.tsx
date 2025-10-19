import React, { useState } from 'react';
import '../styles/PromptModal.css';

interface PromptModalProps {
  onSubmit: (title: string, prompt: string) => void;
  onClose: () => void;
}

const PromptModal: React.FC<PromptModalProps> = ({ onSubmit, onClose }) => {
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!title.trim()) {
      setError('Please enter a feature title');
      return;
    }

    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    onSubmit(title.trim(), prompt.trim());
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal prompt-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">Create New Feature</div>

        <form onSubmit={handleSubmit}>
          {error && <div className="error">{error}</div>}

          <div className="form-group">
            <label htmlFor="title">Feature Title *</label>
            <input
              id="title"
              type="text"
              className="input"
              placeholder="e.g., Add user authentication"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setError('');
              }}
              autoFocus
            />
            <p className="help-text">
              This will be used as the branch name for this feature
            </p>
          </div>

          <div className="form-group">
            <label htmlFor="prompt">Prompt *</label>
            <textarea
              id="prompt"
              className="input textarea"
              placeholder="Describe what you want to build or change..."
              value={prompt}
              onChange={(e) => {
                setPrompt(e.target.value);
                setError('');
              }}
              rows={6}
            />
            <p className="help-text">
              Be specific about what you want the AI agent to implement
            </p>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Create Feature
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PromptModal;
