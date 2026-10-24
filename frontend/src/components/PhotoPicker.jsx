import { useRef } from "react";

const MAX_BYTES = 15 * 1024 * 1024;

export default function PhotoPicker({ idPrefix, busy, onFile, onReject }) {
  const cameraRef = useRef(null);
  const uploadRef = useRef(null);

  const handle = (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("image/")) return onReject("That file isn't an image. Choose a photo.");
    if (file.size > MAX_BYTES) return onReject("Photo is over 15 MB. Choose a smaller photo.");
    onFile(file);
  };

  return (
    <div className="bv-btn-row">
      <button type="button" className="bv-btn" disabled={busy} onClick={() => cameraRef.current.click()} data-testid={`${idPrefix}-take-photo-button`}>
        Take photo
      </button>
      <button type="button" className="bv-btn" disabled={busy} onClick={() => uploadRef.current.click()} data-testid={`${idPrefix}-upload-photo-button`}>
        Upload photo
      </button>
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden tabIndex={-1} aria-hidden="true" onChange={handle} data-testid={`${idPrefix}-camera-input`} />
      <input ref={uploadRef} type="file" accept="image/*" hidden tabIndex={-1} aria-hidden="true" onChange={handle} data-testid={`${idPrefix}-file-input`} />
    </div>
  );
}
