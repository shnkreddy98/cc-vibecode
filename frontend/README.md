# Airfold Apps Frontend

A React-based UI for managing and interacting with Airfold AI-powered development projects.

## Features

- **User Authentication**: Simple username-based login
- **Project Management**: Create, view, and manage multiple projects
- **Interactive Preview**: View your project in an iframe with live updates
- **Click-to-Prompt**: Click anywhere on the preview to create new features with AI
- **Feature Tracking**: Monitor all features and their status (pending, processing, completed, failed)
- **Real-time Updates**: Automatic iframe reload after successful feature implementation

## Prerequisites

- Node.js 18+ and npm (or yarn/pnpm)
- Backend FastAPI server running (will be implemented separately)

## Installation

1. Install dependencies:

```bash
npm install
```

## Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

**Note**: Port 3000 is reserved for the Next.js applications that are being developed, so this UI runs on port 5173 to avoid conflicts.

## Building for Production

```bash
npm run build
```

The production build will be in the `dist/` folder.

## Project Structure

```
frontend/
├── public/
│   └── index.html              # HTML template
├── src/
│   ├── components/
│   │   ├── Login.tsx           # Login page component
│   │   ├── Dashboard.tsx       # Project dashboard
│   │   ├── ProjectViewer.tsx   # Main project viewer with iframe
│   │   └── PromptModal.tsx     # Modal for creating features
│   ├── services/
│   │   └── api.ts              # API service layer
│   ├── styles/
│   │   ├── global.css          # Global styles
│   │   ├── Login.css           # Login page styles
│   │   ├── Dashboard.css       # Dashboard styles
│   │   ├── ProjectViewer.css   # Project viewer styles
│   │   └── PromptModal.css     # Modal styles
│   ├── types/
│   │   └── index.ts            # TypeScript type definitions
│   ├── App.tsx                 # Main app component
│   └── index.tsx               # App entry point
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## How It Works

### 1. Login
Users enter a username to access the application. The username is stored in localStorage for persistence.

### 2. Dashboard
After login, users see their projects. They can:
- Create new projects with repo URL, Neon project name, and preview URL
- View existing projects
- Delete projects
- Open a project to work on it

### 3. Project Viewer
When a project is opened, users see:
- **Left Sidebar**: List of all features created for this project with their status
- **Main Area**: iframe showing the live preview of the project
- **Interactive Overlay**: Transparent overlay that captures clicks

### 4. Creating Features
1. Click anywhere on the preview
2. A modal appears asking for:
   - **Feature Title**: Used to create the git branch name
   - **Prompt**: Description of what to build/change
3. On submit, the feature is sent to the backend `/api/execute` endpoint
4. The agent processes the request and updates the codebase
5. The iframe automatically reloads to show the changes

## API Integration

The frontend expects the following FastAPI endpoints:

### Execute Endpoint
```
POST /api/execute
Body: {
  url: string,           // Git repo URL
  projectName: string,   // Neon project name
  branchName: string,    // Feature branch name
  dirPath: string,       // Temp directory path
  prompt: string,        // User prompt
  first?: boolean        // Is this the first feature?
}
Response: {
  success: boolean,
  message?: string,
  previewUrl?: string
}
```

### Project Endpoints
```
GET /api/projects?username=<username>
POST /api/projects
GET /api/projects/:id
DELETE /api/projects/:id
```

### Feature Endpoints
```
GET /api/features?projectId=<projectId>
POST /api/features
```

## Configuration

### Preview URL
Each project has a `previewUrl` field that points to where the application is running. This is what gets loaded in the iframe. If not specified, it defaults to `http://localhost:3000`.

**Important**: The backend automatically starts each project's Next.js dev server on port 3000. If you need to preview multiple projects simultaneously, you'll need to implement dynamic port allocation.

### API Proxy
The Vite dev server is configured to proxy `/api` requests to `http://localhost:8000`. Update `vite.config.ts` if your backend runs on a different port.

## Fallback Behavior

The UI includes localStorage fallback for when the backend is not available:
- Projects are stored in `localStorage` with key `projects_<username>`
- Features are stored in `localStorage` with key `features_<projectId>`

This allows the UI to be tested independently before the backend is fully implemented.

## Next Steps

1. Implement the FastAPI backend with the required endpoints
2. Convert the `execute` function from `main.py` to a FastAPI endpoint
3. Add authentication/authorization if needed
4. Add WebSocket support for real-time feature status updates
5. Implement project deployment and hosting

## Technology Stack

- **React 18**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **Axios**: HTTP client
- **CSS3**: Styling (no framework to keep it lightweight)

## Browser Support

Modern browsers with ES2020 support:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
