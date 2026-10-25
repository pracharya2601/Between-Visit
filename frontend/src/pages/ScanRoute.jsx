import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";
import ScanPlacement from "@/components/scan/ScanPlacement";
import ScanPictures from "@/components/scan/ScanPictures";

export default function ScanRoute() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [scan, setScan] = useState(null);
  const [error, setError] = useState("");
  const [cancelError, setCancelError] = useState("");
  useTitle(scan?.status === "placed" ? "Scan route: checkpoint pictures" : "Scan route: place the route");

  useEffect(() => {
    axios.get(`${API}/scans/${id}`).then((r) => setScan(r.data)).catch(() => setError("Scan not found"));
  }, [id]);

  const onCancel = async () => {
    try {
      await axios.post(`${API}/scans/${id}/cancel`);
      navigate("/routes");
    } catch {
      setCancelError("Couldn't delete the scan. Try again.");
    }
  };

  if (error || !scan) return <div role="status" aria-live="polite">{error ? <p className="bv-error" data-testid="scan-error">{error}</p> : <p>Loading the scan…</p>}</div>;
  const live = scan.status === "ready" || scan.status === "placed";
  return (
    <div className="bv-stack">
      <section aria-labelledby="scan-route-heading">
        <p className="bv-eyebrow">Create from 3D scan · {scan.route_name}</p>
        <h1 id="scan-route-heading" className="bv-h1">{scan.status === "placed" ? "Checkpoint pictures" : "Place the route"}</h1>
        {live && <button type="button" className="bv-btn bv-btn-danger" onClick={onCancel} data-testid="scan-cancel-button">Cancel and delete this scan</button>}
        <p role="alert" className="bv-error-text" data-testid="scan-cancel-error">{cancelError}</p>
      </section>
      {scan.status === "ready" && scan.scene && <ScanPlacement scan={scan} onScan={setScan} />}
      {scan.status === "placed" && scan.scene && <ScanPictures scan={scan} />}
      {!live && (
        <p data-testid="scan-final-state">
          {scan.status === "saved" ? "This scan route is saved." : scan.error || "This scan isn't available any more."} <Link to="/routes" className="bv-link" data-testid="scan-back-to-routes">Back to Routes</Link>
        </p>
      )}
    </div>
  );
}
