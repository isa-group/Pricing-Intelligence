import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import type { ChatMessage } from '../types';

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
}

function ChatTranscript({ messages, isLoading }: Props) {
  return (
    <div className="chat-transcript">
      {messages.length === 0 && !isLoading ? (
        <div className="empty-state">No messages yet. Ask about a pricing page to get started.</div>
      ) : null}
      {messages.map((message) => (
        <article key={message.id} className={`message message-${message.role}`}>
          <header>
            <span className="message-role">{message.role === 'user' ? 'You' : 'Assistant'}</span>
            <time dateTime={message.createdAt}>{new Date(message.createdAt).toLocaleTimeString()}</time>
          </header>
          <div className="message-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
          {message.metadata?.plan || message.metadata?.result ? (
            <details>
              <summary>View assistant context</summary>
              {message.metadata.plan ? (
                <>
                  <h4>Planner</h4>
                  <pre>{JSON.stringify(message.metadata.plan, null, 2)}</pre>
                </>
              ) : null}
              {message.metadata.result ? (
                <>
                  <h4>Result</h4>
                  <pre>{JSON.stringify(message.metadata.result, null, 2)}</pre>
                </>
              ) : null}
            </details>
          ) : null}
        </article>
      ))}
      {isLoading ? <div className="message message-assistant">Processing request...</div> : null}
    </div>
  );
}

export default ChatTranscript;
