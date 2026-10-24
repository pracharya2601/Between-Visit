import { useEffect, useRef } from "react";

export default function EndConfirm({ onConfirm, onCancel }) {
  const ref = useRef(null);
  useEffect(() => { ref.current?.focus(); }, []);
  return (
    <section role="alertdialog" aria-labelledby="end-confirm-heading" className="bv-run-section bv-panel" data-testid="end-confirm">
      <h2 id="end-confirm-heading" ref={ref} tabIndex={-1} className="bv-run-question">End this run?</h2>
      <button type="button" className="bv-btn bv-run-btn bv-run-end" onClick={onConfirm} data-testid="end-confirm-button">Yes, end the run</button>
      <button type="button" className="bv-btn bv-run-btn" onClick={onCancel} data-testid="end-cancel-button">Cancel, keep going</button>
    </section>
  );
}
