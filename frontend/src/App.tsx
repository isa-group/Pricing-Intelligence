import { FormEvent, useEffect, useMemo, useState } from 'react';

import ChatTranscript from './components/ChatTranscript';
import ControlPanel from './components/ControlPanel';
import type { ChatMessage, ChatPayload } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8085';

const extractPricingUrl = (text: string): string | undefined => {
  const urlRegex = /(https?:\/\/[^\s]+)/i;
  const match = text.match(urlRegex);
  if (!match) {
    return undefined;
  }

  const candidate = match[0].replace(/[),.;]+$/, '');
  try {
    const url = new URL(candidate);
    return url.href;
  } catch (error) {
    console.warn('Detected invalid pricing URL candidate', candidate, error);
    return undefined;
  }
};

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [payload, setPayload] = useState<ChatPayload>({
    question: '',
    pricingYaml: undefined
  });
  const [selectedFileName, setSelectedFileName] = useState<string | undefined>(undefined);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') {
      return 'light';
    }
    const stored = window.localStorage.getItem('pricing-theme');
    if (stored === 'light' || stored === 'dark') {
      return stored;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  const detectedPricingUrl = useMemo(() => extractPricingUrl(payload.question), [payload.question]);

  const isSubmitDisabled = useMemo(() => {
    const hasQuestion = Boolean(payload.question.trim());
    return isLoading || !hasQuestion;
  }, [payload.question, isLoading]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('pricing-theme', theme);
    }
  }, [theme]);

  const handleChange = (updated: Partial<ChatPayload>) => {
    setPayload((prev: ChatPayload) => ({ ...prev, ...updated }));
  };

  const toggleTheme = () => {
    setTheme((previous: 'light' | 'dark') => (previous === 'dark' ? 'light' : 'dark'));
  };

  const handleFileSelect = (file: File | null) => {
    if (!file) {
      setSelectedFileName(undefined);
      setPayload((prev: ChatPayload) => ({ ...prev, pricingYaml: undefined }));
      return;
    }

    setSelectedFileName(file.name);
    file
      .text()
      .then((content) => {
        setPayload((prev: ChatPayload) => ({ ...prev, pricingYaml: content }));
      })
      .catch((error) => {
        console.error('Failed to read YAML file', error);
        setSelectedFileName(undefined);
        setPayload((prev: ChatPayload) => ({ ...prev, pricingYaml: undefined }));
        setMessages((prev: ChatMessage[]) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: 'Could not read the uploaded file. Please try again.',
            createdAt: new Date().toISOString()
          }
        ]);
      });
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (isSubmitDisabled) return;

    const question = payload.question.trim();

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      createdAt: new Date().toISOString()
    };
    setMessages((prev: ChatMessage[]) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const body: Record<string, unknown> = {
        question
      };

      if (detectedPricingUrl) {
        body.pricing_url = detectedPricingUrl;
      }

      if (payload.pricingYaml && payload.pricingYaml.trim()) {
        body.pricing_yaml = payload.pricingYaml;
      }

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        let message = `API returned ${response.status}`;
        try {
          const detail = await response.json();
          if (typeof detail?.detail === 'string') {
            message = detail.detail;
          }
        } catch (parseError) {
          console.error('Failed to parse error response', parseError);
        }
        throw new Error(message);
      }

      const data = await response.json();
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer ?? 'No response available.',
        createdAt: new Date().toISOString(),
        metadata: {
          plan: data.plan ?? undefined,
          result: data.result ?? undefined
        }
      };
      setMessages((prev: ChatMessage[]) => [...prev, assistantMessage]);
    } catch (error) {
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Error: ${(error as Error).message}`,
        createdAt: new Date().toISOString()
      };
      setMessages((prev: ChatMessage[]) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
      setPayload((prev: ChatPayload) => ({ ...prev, question: '' }));
    }
  };

  return (
    <div className="app">
      <header className="header-bar">
        <div>
          <h1>Pricing Intelligence Assistant</h1>
          <p>Ask about optimal subscriptions and pricing insights using the MCP server.</p>
        </div>
        <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label="Toggle color theme">
          {theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        </button>
      </header>
      <main>
        <section className="chat-panel">
          <ChatTranscript messages={messages} isLoading={isLoading} />
        </section>
        <section className="control-panel">
          <ControlPanel
            payload={payload}
            detectedPricingUrl={detectedPricingUrl}
            isSubmitting={isLoading}
            isSubmitDisabled={isSubmitDisabled}
            onChange={handleChange}
            onSubmit={handleSubmit}
            onFileSelect={handleFileSelect}
            selectedFileName={selectedFileName}
          />
        </section>
      </main>
    </div>
  );
}

export default App;
