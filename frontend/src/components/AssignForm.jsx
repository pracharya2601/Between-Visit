import { useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

const STOP_RULE = "If you feel unsure, stop, press Help and wait for my call.";
const GOAL_HINT = "Walk from the entrance to the reception desk using the three landmarks";

function validate(f) {
  const e = {};
  if (!f.client_id) e.client_id = "Choose a client.";
  if (!f.goal.trim()) e.goal = "Enter a goal.";
  if (!f.stop_rule.trim()) e.stop_rule = "Enter a stop-and-contact rule.";
  return e;
}

const FieldError = ({ id, text }) => (text ? <p id={id} className="bv-error-text bv-field-error" data-testid={id}>{text}</p> : null);

export default function AssignForm({ routeId, clients, onCreated }) {
  const [f, setF] = useState({ client_id: "", goal: "", cue_style: "standard", stay_silent_on_route: true, no_repeat: true, note: "", stop_rule: STOP_RULE, record_demo: false });
  const [errors, setErrors] = useState({});
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const err = (k) => (errors[k] ? { "aria-invalid": true, "aria-describedby": `${k}-error` } : {});

  const onSubmit = async (e) => {
    e.preventDefault();
    const v = validate(f);
    setErrors(v);
    if (Object.keys(v).length) return setStatus("Fix the highlighted fields.");
    setBusy(true);
    setStatus("Assigning…");
    try {
      const r = await axios.post(`${API}/routes/${routeId}/exercises`, f);
      onCreated(r.data);
    } catch (ex) {
      const d = ex.response?.data?.detail;
      setStatus(typeof d === "string" ? d : "Couldn't assign the exercise. Try again.");
      setBusy(false);
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="bv-panel" aria-labelledby="assign-form-heading" data-testid="assign-form">
      <h2 id="assign-form-heading" className="bv-h2">Exercise details</h2>
      <div className="bv-field">
        <label htmlFor="client_id" className="bv-label">Client</label>
        <select id="client_id" className="bv-input" value={f.client_id} onChange={set("client_id")} {...err("client_id")} data-testid="assign-client-select">
          <option value="">Choose a client</option>
          {clients.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}
        </select>
        <FieldError id="client_id-error" text={errors.client_id} />
      </div>
      <div className="bv-field">
        <label htmlFor="goal" className="bv-label">Goal</label>
        <textarea id="goal" rows={2} className="bv-input" placeholder={GOAL_HINT} value={f.goal} onChange={set("goal")} {...err("goal")} data-testid="assign-goal-input" />
        <FieldError id="goal-error" text={errors.goal} />
      </div>
      <fieldset className="bv-fieldset">
        <legend className="bv-label">Cue style</legend>
        {[["minimal", "Minimal (checkpoint names only)"], ["standard", "Standard (checkpoint plus landmark)"]].map(([v, label]) => (
          <label key={v} className="bv-choice">
            <input type="radio" name="cue_style" value={v} checked={f.cue_style === v} onChange={set("cue_style")} data-testid={`assign-cue-${v}-radio`} />
            <span>{label}</span>
          </label>
        ))}
      </fieldset>
      <fieldset className="bv-fieldset">
        <legend className="bv-label">Silence rules</legend>
        <label className="bv-choice">
          <input type="checkbox" checked={f.stay_silent_on_route} onChange={set("stay_silent_on_route")} data-testid="assign-stay-silent-checkbox" />
          <span>Stay silent while on route</span>
        </label>
        <label className="bv-choice">
          <input type="checkbox" checked={f.no_repeat} onChange={set("no_repeat")} data-testid="assign-no-repeat-checkbox" />
          <span>Don't repeat a cue for the same thing</span>
        </label>
        <label htmlFor="note" className="bv-label bv-label-spaced">Silence note (optional)</label>
        <input id="note" className="bv-input" value={f.note} onChange={set("note")} data-testid="assign-note-input" />
      </fieldset>
      <label className="bv-choice bv-label-spaced">
        <input type="checkbox" checked={f.record_demo} onChange={set("record_demo")} data-testid="assign-record-demo-checkbox" />
        <span>Record this run as a demo (empty space, team only)</span>
      </label>
      <div className="bv-field">
        <label htmlFor="stop_rule" className="bv-label">Stop-and-contact rule</label>
        <textarea id="stop_rule" rows={2} className="bv-input" value={f.stop_rule} onChange={set("stop_rule")} {...err("stop_rule")} data-testid="assign-stop-rule-input" />
        <FieldError id="stop_rule-error" text={errors.stop_rule} />
      </div>
      <button type="submit" className="bv-btn bv-btn-primary" disabled={busy} data-testid="assign-submit-button">Assign exercise</button>
      <p aria-live="polite" role="status" className="bv-cp-msg" data-testid="assign-status">{status}</p>
    </form>
  );
}
