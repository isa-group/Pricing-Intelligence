import { ChangeEvent, FormEvent } from 'react';

import type { ChatPayload } from '../types';

interface Props {
  payload: ChatPayload;
  detectedPricingUrls?: string[];
  isSubmitting: boolean;
  isSubmitDisabled: boolean;
  onChange: (payload: Partial<ChatPayload>) => void;
  onSubmit: (event: FormEvent) => void;
  onFileSelect: (files: FileList | null) => void;
  onClearFiles: () => void;
  selectedFileNames?: string[];
}

function ControlPanel({
  payload,
  detectedPricingUrls,
  isSubmitting,
  isSubmitDisabled,
  onChange,
  onSubmit,
  onFileSelect,
  onClearFiles,
  selectedFileNames
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
        {detectedPricingUrls && detectedPricingUrls.length > 0 ? (
          <span className="help-text">
            Detected pricing URL{detectedPricingUrls.length > 1 ? 's' : ''}:{' '}
            {detectedPricingUrls.join(', ')}
          </span>
        ) : (
          <span className="help-text">
            Optional context: mention a pricing URL or attach a Pricing2Yaml file if you want grounded insights. Otherwise H.A.R.V.E.Y. will answer with general guidance.
          </span>
        )}
      </div>

      <label>
        Upload pricing YAML (optional)
        <input
          type="file"
          accept=".yaml,.yml"
          multiple
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            const files = event.target.files ?? null;
            onFileSelect(files);
            event.target.value = '';
          }}
        />
        <span className="help-text">
          {selectedFileNames && selectedFileNames.length > 0
            ? `Selected file${selectedFileNames.length > 1 ? 's' : ''}: ${selectedFileNames.join(', ')}`
            : 'Provide one or more YAML exports to help H.A.R.V.E.Y. analyse local pricing.'}
        </span>
        {selectedFileNames && selectedFileNames.length > 0 ? (
          <button
            type="button"
            className="clear-files-button"
            onClick={onClearFiles}
          >
            Clear uploads
          </button>
        ) : null}
      </label>

      <button type="submit" disabled={isSubmitDisabled}>
        {isSubmitting ? 'Processing...' : 'Ask'}
      </button>
    </form>
  );
}

export default ControlPanel;
