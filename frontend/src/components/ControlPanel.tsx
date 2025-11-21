import { ChangeEvent, FormEvent, useState } from "react";
import ContextManager from "./ContextManager";
import type { ContextItemInput, PricingContextItem } from "../types";
import SearchPricings from "./SearchPricings";
import Modal from "./Modal";

interface Props {
  question: string;
  detectedPricingUrls: string[];
  contextItems: PricingContextItem[];
  isSubmitting: boolean;
  isSubmitDisabled: boolean;
  onQuestionChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onFileSelect: (files: FileList | null) => void;
  onContextAdd: (input: ContextItemInput) => void;
  onContextRemove: (id: string) => void;
  onContextClear: () => void;
}

function ControlPanel({
  question,
  detectedPricingUrls,
  contextItems,
  isSubmitting,
  isSubmitDisabled,
  onQuestionChange,
  onSubmit,
  onFileSelect,
  onContextAdd,
  onContextRemove,
  onContextClear,
}: Props) {
  const [showPricingModal, setPricingModal] = useState<boolean>(false);

  const handleQuestionChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    onQuestionChange(event.target.value);
  };

  const handleOpenModal = () => setPricingModal(true);
  const handleCloseModal = () => setPricingModal(false);

  return (
    <>
      <form className="control-form" onSubmit={onSubmit}>
        <label>
          Question
          <textarea
            name="question"
            required
            rows={4}
            value={question}
            onChange={handleQuestionChange}
            placeholder="Which is the best available subscription for a team of five users?"
          />
        </label>

        <ContextManager
          items={contextItems}
          detectedUrls={detectedPricingUrls}
          onAdd={onContextAdd}
          onRemove={onContextRemove}
          onClear={onContextClear}
        />

        <label className="file-upload">
          Upload pricing YAML (optional)
          <input
            type="file"
            accept=".yaml,.yml"
            multiple
            onChange={(event: ChangeEvent<HTMLInputElement>) => {
              const files = event.target.files ?? null;
              onFileSelect(files);
              event.target.value = "";
            }}
          />
          <span className="help-text">
            Uploaded YAMLs appear in the pricing context above so you can remove
            them at any time.
          </span>
        </label>

        <div className="control-actions">
          <button type="submit" disabled={isSubmitDisabled}>
            {isSubmitting ? "Processing..." : "Ask"}
          </button>
        </div>
      </form>
      <section>
        <h3> Add SPHERE iPricing to context (optional)</h3>
        <button
          type="button"
          className="context-add-url"
          onClick={handleOpenModal}
        >
          Search pricings
        </button>
        <Modal open={showPricingModal} onClose={handleCloseModal}>
          <SearchPricings
            onContextAdd={onContextAdd}
          />
        </Modal>
      </section>
    </>
  );
}

export default ControlPanel;
