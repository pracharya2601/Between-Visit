import { useState } from "react";

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
}

export default function CopyField({ id, label, value }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    await copyText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="bv-field">
      <label htmlFor={id} className="bv-label">{label}</label>
      <div className="bv-copy-row">
        <input id={id} readOnly value={value} className="bv-input bv-mono" data-testid={`${id}-value`} />
        <button type="button" className="bv-btn" onClick={onCopy} aria-label={`Copy ${label}`} data-testid={`${id}-copy-button`}>
          Copy
        </button>
      </div>
      <p aria-live="polite" className="bv-hint" data-testid={`${id}-copy-status`}>{copied ? `${label} copied` : ""}</p>
    </div>
  );
}
