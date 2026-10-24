export function saveBlocker(name, cps) {
  if (!name.trim()) return "Add a route name to save.";
  if (!cps.length) return "Add at least one checkpoint to save.";
  const ok = cps.filter((c) => c.approved).length;
  if (ok < cps.length) return `Approve every checkpoint to save (${ok} of ${cps.length} approved).`;
  return "";
}
