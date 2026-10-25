import { useEffect, useRef } from "react";

const FOCUSABLE = "button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";

// Moves focus into an inline confirm dialog, keeps Tab inside it, closes on Escape and restores focus on close.
export function useDialogFocus(onEscape, restoreSelector) {
  const boxRef = useRef(null);
  const startRef = useRef(null);
  useEffect(() => {
    const opener = document.activeElement;
    (startRef.current || boxRef.current)?.focus();
    const box = boxRef.current;
    const onKey = (e) => {
      if (e.key === "Escape" && onEscape) return onEscape();
      if (e.key !== "Tab" || !box) return;
      const items = [...box.querySelectorAll(FOCUSABLE)];
      if (!items.length) return;
      const [first, last] = [items[0], items[items.length - 1]];
      if (e.shiftKey && (document.activeElement === first || document.activeElement === startRef.current)) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    box?.addEventListener("keydown", onKey);
    return () => {
      box?.removeEventListener("keydown", onKey);
      setTimeout(() => {
        const target = opener && document.contains(opener) ? opener : restoreSelector && document.querySelector(restoreSelector);
        target?.focus();
      }, 0);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { boxRef, startRef };
}
