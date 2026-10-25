import { useParams } from "react-router-dom";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";
import { useApi } from "@/hooks/useApi";
import { FOOTER_TEXT } from "@/components/Layout";

const when = (iso, time) => new Date(iso).toLocaleString([], { year: "numeric", month: "long", day: "numeric", ...(time ? { hour: "2-digit", minute: "2-digit", hour12: false } : {}) });

export default function NotePrint() {
  useTitle("Progress note (print)");
  const { id } = useParams();
  const { status, data, code } = useApi(`${API}/notes/${id}`);
  return (
    <>
    <a href="#main" className="bv-skip bv-noprint" data-testid="skip-to-content-link">Skip to main content</a>
    <main id="main" tabIndex={-1} className="bv-print" data-testid="note-print-page">
      {status === "loading" && <p role="status">Loading the note…</p>}
      {status === "error" && <h1 className="bv-error bv-h1" role="status" data-testid="note-print-error">{code === 404 ? "Note not found" : "Couldn't load the note"}</h1>}
      {status === "ready" && (
        <article aria-labelledby="note-print-heading">
          <p className="bv-eyebrow">Progress note</p>
          <h1 id="note-print-heading" className="bv-h1" data-testid="note-print-client">{data.client_name || "Progress note"}</h1>
          <dl className="bv-dl">
            <dt>Date</dt><dd data-testid="note-print-date">{when(data.attempt_date)}</dd>
            <dt>Route</dt><dd data-testid="note-print-route">{data.route_name} · v{data.route_version}</dd>
          </dl>
          <p className="bv-note-text" data-testid="note-print-text">{data.text}</p>
          <p className="bv-strong" data-testid="note-print-author">Approved by {data.author}, {when(data.approved_at, true)}</p>
          <button type="button" className="bv-btn bv-btn-primary bv-noprint" onClick={() => window.print()} data-testid="note-print-button">Print this note</button>
        </article>
      )}
      <footer className="bv-print-footer" data-testid="note-print-footer">{FOOTER_TEXT}</footer>
    </main>
    </>
  );
}
