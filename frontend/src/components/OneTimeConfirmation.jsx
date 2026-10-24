import { useEffect, useRef } from "react";
import CopyField from "@/components/CopyField";

export const runPath = (attemptId) => `/run/${attemptId}`;

export default function OneTimeConfirmation({ title, created, onClose }) {
  const headingRef = useRef(null);
  useEffect(() => { headingRef.current?.focus(); }, []);
  const { attempt, key } = created;
  const link = `${window.location.origin}${runPath(attempt.id)}#key=${key}`;

  return (
    <section className="bv-panel bv-confirm" aria-labelledby="confirm-heading" data-testid="one-time-confirmation">
      <h2 id="confirm-heading" ref={headingRef} tabIndex={-1} className="bv-h2">{title}</h2>
      <p className="bv-warning" role="alert" data-testid="key-shown-once-warning">
        The key is shown only once. Copy the run link now. After you close this, the key can't be shown again; if it's lost, make a new attempt.
      </p>
      <CopyField id="run-link" label="Run link" value={link} />
      <CopyField id="new-stream-id" label="Stream ID" value={attempt.stream_id} />
      <CopyField id="new-key" label="Key" value={key} />
      <p data-testid="client-sees-note">The client also sees these on their run page.</p>
      <button type="button" className="bv-btn bv-btn-primary" onClick={onClose} data-testid="close-confirmation-button">
        I've copied it, close
      </button>
    </section>
  );
}
