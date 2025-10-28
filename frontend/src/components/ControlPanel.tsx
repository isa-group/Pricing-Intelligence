import { ChangeEvent, FormEvent } from 'react';

import type { ChatPayload } from '../types';

interface Props {
  payload: ChatPayload;
  detectedPricingUrl?: string;
  isSubmitting: boolean;
  isSubmitDisabled: boolean;
  onChange: (payload: Partial<ChatPayload>) => void;
  onSubmit: (event: FormEvent) => void;
  onFileSelect: (file: File | null) => void;
  selectedFileName?: string;
}

function ControlPanel({
  payload,
  detectedPricingUrl,
  isSubmitting,
  isSubmitDisabled,
  onChange,
  onSubmit,
  onFileSelect,
  selectedFileName
}: Props) {
  const handleTextChange = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target;
    onChange({ [name]: value } as Partial<ChatPayload>);
  };

  return (
    <form className="control-form" onSubmit={onSubmit}>
      <label>
        Question
        <textarea
          name="question"
          required
          rows={4}
          value={payload.question}
          onChange={handleTextChange}
          placeholder="What is the best plan for a team of five?"
        />
      </label>

      <div className="detected-context">
        {detectedPricingUrl ? (
          <span className="help-text">Detected pricing URL: {detectedPricingUrl}</span>
        ) : (
          <span className="help-text">
            Optional context: mention a pricing URL or attach a Pricing2Yaml file if you want grounded insights. Otherwise the assistant will answer with general guidance.
          </span>
        )}
      </div>

      <label>
        Upload pricing YAML (optional)
        <input
          type="file"
          accept=".yaml,.yml"
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            const file = event.target.files?.[0] ?? null;
            onFileSelect(file);
            event.target.value = '';
          }}
        />
        <span className="help-text">
          {selectedFileName ? `Selected file: ${selectedFileName}` : 'Provide a YAML export to analyse local pricing.'}
        </span>
      </label>

      <button type="submit" disabled={isSubmitDisabled}>
        {isSubmitting ? 'Processing...' : 'Ask'}
      </button>
    </form>
  );
}

export default ControlPanel;
