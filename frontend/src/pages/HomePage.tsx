import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { FileText, Shield, Search, Zap } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="text-center max-w-3xl mx-auto">
          <FileText className="h-16 w-16 text-primary mx-auto mb-6" />
          <h1 className="text-5xl font-bold mb-6">T&C Analysis System</h1>
          <p className="text-xl text-gray-600 mb-8">
            Instantly analyze Terms & Conditions documents. Detect risky clauses, ask questions,
            and understand legal agreements with AI-powered insights.
          </p>
          <div className="flex gap-4 justify-center">
            <Button size="lg" asChild>
              <Link to="/signup">Get Started</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/login">Login</Link>
            </Button>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-24">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <Shield className="h-12 w-12 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Anomaly Detection</h3>
            <p className="text-gray-600">
              Automatically detect unusual or risky clauses by comparing against 100+ standard T&Cs.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <Search className="h-12 w-12 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Smart Q&A</h3>
            <p className="text-gray-600">
              Ask questions about any document and get accurate answers with citations to specific clauses.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <Zap className="h-12 w-12 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Instant Analysis</h3>
            <p className="text-gray-600">
              Upload a PDF and get comprehensive analysis in seconds, powered by advanced AI models.
            </p>
          </div>
        </div>

        {/* How it Works */}
        <div className="mt-24 text-center">
          <h2 className="text-3xl font-bold mb-12">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <div className="bg-primary text-white rounded-full w-12 h-12 flex items-center justify-center text-xl font-bold mx-auto mb-4">
                1
              </div>
              <h4 className="font-semibold mb-2">Upload Document</h4>
              <p className="text-gray-600">Upload your Terms & Conditions PDF document</p>
            </div>
            <div>
              <div className="bg-primary text-white rounded-full w-12 h-12 flex items-center justify-center text-xl font-bold mx-auto mb-4">
                2
              </div>
              <h4 className="font-semibold mb-2">AI Analysis</h4>
              <p className="text-gray-600">Our AI analyzes every clause and detects anomalies</p>
            </div>
            <div>
              <div className="bg-primary text-white rounded-full w-12 h-12 flex items-center justify-center text-xl font-bold mx-auto mb-4">
                3
              </div>
              <h4 className="font-semibold mb-2">Get Insights</h4>
              <p className="text-gray-600">View results, ask questions, and understand the risks</p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t bg-white mt-24">
        <div className="container mx-auto px-4 py-8 text-center text-gray-600">
          <p>© 2024 T&C Analysis System. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
