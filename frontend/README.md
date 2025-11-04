# Frontend Directory

This directory contains the React + TypeScript frontend application for the T&C Analysis System.

## Structure

```
frontend/
├── public/                # Static assets
├── src/
│   ├── components/       # React components
│   │   ├── common/      # Shared components
│   │   ├── upload/      # Upload interface
│   │   ├── analysis/    # Analysis display
│   │   └── qa/          # Q&A chat interface
│   ├── pages/           # Page components
│   ├── hooks/           # Custom React hooks
│   ├── services/        # API services
│   ├── types/           # TypeScript types
│   └── utils/           # Utility functions
├── package.json
└── vite.config.ts
```

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env
# Edit .env with backend API URL

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Development Server

Visit http://localhost:5173 after starting the dev server.

## Key Features

### Upload Interface
Drag-and-drop PDF upload with progress tracking and validation.

### Analysis Dashboard
Display document analysis results including:
- Company name and metadata
- Section/clause count
- Processing status
- Risk score

### Anomaly Report Viewer
Interactive display of detected anomalies:
- High-risk clauses highlighted
- Risk explanations in plain language
- Prevalence statistics
- Missing clauses section

### Q&A Chat Interface
Ask questions about the document:
- Natural language questions
- Answers with section citations
- Risk warnings when applicable
- Related anomalies highlighted

### Comparison Tool
Side-by-side comparison of multiple T&Cs:
- Compare specific aspects (cancellation, privacy, etc.)
- Highlight key differences
- Identify most user-friendly option

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (optional)
- **State Management**: React Query
- **Routing**: React Router
- **HTTP Client**: Axios

## Environment Variables

```env
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=T&C Analysis System
```

## Available Scripts

```bash
# Development
npm run dev          # Start dev server
npm run build        # Build for production
npm run preview      # Preview production build

# Code Quality
npm run lint         # Run ESLint
npm run format       # Format with Prettier
npm run type-check   # TypeScript type checking

# Testing
npm test             # Run tests
npm test -- --watch  # Run tests in watch mode
```

## Deployment

### Netlify

```bash
# Build command
npm run build

# Publish directory
dist

# Environment variables (add in Netlify dashboard)
VITE_API_URL=https://your-backend-url.com
```

### Vercel

```bash
# Build command
npm run build

# Output directory
dist
```

## Component Structure

### Common Components
- `Header.tsx` - Navigation header
- `Footer.tsx` - Page footer
- `LoadingSpinner.tsx` - Loading indicator
- `Button.tsx` - Reusable button component

### Upload Components
- `UploadArea.tsx` - Drag-and-drop zone
- `UploadProgress.tsx` - Upload progress bar
- `FilePreview.tsx` - File info display

### Analysis Components
- `AnomalyReport.tsx` - Full anomaly report
- `RiskScore.tsx` - Risk score visualization
- `ClauseCard.tsx` - Individual clause display
- `AnomalyCard.tsx` - Anomaly detail card

### Q&A Components
- `ChatInterface.tsx` - Main chat UI
- `MessageBubble.tsx` - Chat message display
- `QueryInput.tsx` - Question input field

## API Integration

All API calls go through services:

```typescript
// src/services/documentService.ts
export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload', formData);
  return response.data;
};

// Usage in component
const { mutate: uploadDoc } = useMutation({
  mutationFn: uploadDocument,
  onSuccess: (data) => {
    console.log('Document uploaded:', data);
  }
});
```

## State Management

Using React Query for server state:

```typescript
// Fetch document
const { data: document } = useQuery({
  queryKey: ['document', documentId],
  queryFn: () => getDocument(documentId),
});

// Upload document
const { mutate: upload } = useMutation({
  mutationFn: uploadDocument,
});
```

## Styling

Using Tailwind CSS utility classes:

```tsx
<div className="flex items-center justify-center p-4 bg-blue-500 text-white rounded-lg">
  Click to upload
</div>
```

## Type Safety

All API responses have TypeScript types:

```typescript
// src/types/document.ts
export interface Document {
  id: number;
  filename: string;
  company_name: string;
  effective_date: string | null;
  num_sections: number;
  num_clauses: number;
  processing_status: 'processing' | 'completed' | 'failed';
  created_at: string;
}
```

## Testing

```bash
# Run tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

## Next Steps

1. Set up routing (Week 9)
2. Create upload page (Week 9)
3. Build analysis dashboard (Week 9)
4. Implement Q&A interface (Week 9)
5. Add comparison tool (Week 10)
6. Style and polish (Week 10)
7. Deploy to Netlify (Week 10)

## Resources

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [React Query](https://tanstack.com/query/latest)
