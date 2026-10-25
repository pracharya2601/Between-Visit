import { useState } from "react";

export default function MachineView({ machine, testId }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState("");
  const json = JSON.stringify(machine, null, 2);
  const copy = () => navigator.clipboard.writeText(json).then(() => setCopied("Copied")).catch(() => setCopied("Couldn't copy"));
  return (
    <div className="bv-machine" data-testid={testId}>
      <button type="button" className="bv-btn bv-btn-small" aria-expanded={open} aria-controls={`${testId}-json`} onClick={() => setOpen((o) => !o)} data-testid={`${testId}-toggle`}>Machine view</button>
      {open && (
        <>
          <pre id={`${testId}-json`} className="bv-tl-json" aria-label="Machine view JSON, read-only" data-testid={`${testId}-json`}>{json}</pre>
          <button type="button" className="bv-btn bv-btn-small" onClick={copy} data-testid={`${testId}-copy`}>Copy JSON</button>
          <span role="status" aria-live="polite" className="bv-strong" data-testid={`${testId}-copy-status`}> {copied}</span>
        </>
      )}
    </div>
  );
}
