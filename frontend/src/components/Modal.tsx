import { useEffect } from "react";
import { createPortal } from "react-dom";

interface ModalProps {
  open: boolean;
  children: React.ReactElement;
  onClose: () => void;
}

function Modal({ open, children, onClose }: ModalProps) {
  
    const handleCloseKeyboard = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      onClose();
    }
  };

  useEffect(() => {
    window.addEventListener("keydown", handleCloseKeyboard);
    return () => window.removeEventListener("keydown", handleCloseKeyboard);
  });

  if (!open) {
    return null;
  }

  return createPortal(
    <>
      <div className="modal-overlay"></div>
      <div className="modal-content">
        <button
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              onClose();
            }
          }}
          onClick={onClose}
        >
          Close Modal
        </button>
        {children}
      </div>
    </>,
    document.getElementById("portal") as HTMLElement
  );
}

export default Modal;
