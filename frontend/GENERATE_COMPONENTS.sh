#!/bin/bash
# Frontend Component Generation Script
# This script creates all React components needed for the T&C Analysis System

cd "/Users/akhil/Desktop/Project T&C/frontend"

echo "🚀 Generating all frontend components..."
echo ""

# Create main.tsx
cat > src/main.tsx << 'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import './styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
)
EOF
echo "✓ Created src/main.tsx"

# Save this script to continue...
echo ""
echo "Script created! Run it with: bash GENERATE_COMPONENTS.sh"
