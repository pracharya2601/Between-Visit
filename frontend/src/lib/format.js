export const mss = (s) => {
  const t = Math.max(0, Math.round(s));
  const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), sec = String(t % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
};

export const dotLabel = (i) => `${i.category === "spoken" ? "Spoken" : "Suppressed"} cue at ${mss(i.at)}: ${i.text}`;
