export default function groupMetrics(metrics) {
  const groups = new Map();
  for (const metric of metrics.filter((item) => !item.deleted)) {
    if (!groups.has(metric.code)) groups.set(metric.code, []);
    groups.get(metric.code).push(metric);
  }
  return [...groups.entries()].map(([code, items]) => {
    const versions = [...items].sort((a, b) => b.version - a.version);
    const approved = versions.find((item) => item.status === 'approved');
    const working = versions.find(
      (item) =>
        ['draft', 'submitted', 'rejected'].includes(item.status) &&
        (!approved || item.version > approved.version),
    );
    const primary = approved || working || versions[0];
    const history = versions.filter(
      (item) => item.id !== primary.id && item.id !== working?.id,
    );
    return { code, approved, working, primary, history };
  });
}
