// Chuyển tên trường API sang cấu trúc mà các bảng hiện tại đang hiển thị.
export function metricFromApi(item) {
  return {
    ...item,
    type: item.formula_type,
    terms: item.formula_params?.terms ?? 1,
    threshold: item.threshold?.value,
    operator: item.threshold?.operator,
    status: item.status === 'pending' ? 'submitted' : item.status,
  };
}
export function resultFromApi(item) {
  return {
    ...item,
    student: item.learner_id,
    metric: item.metric_definition_id,
    version: item.metric_version,
    flag: item.flagged,
    date: item.computed_at,
    term: `${item.academic_year} · HK${item.semester}`,
  };
}
export function alertFromApi(item) {
  return {
    ...item,
    student: item.learner.id,
    metric: `${item.metric_result.metric_code}@${item.metric_result.metric_version}`,
    value: item.metric_result.value,
    version: item.metric_result.metric_version,
    threshold: item.metric_result.threshold?.value,
    status: item.status === 'pending_review' ? 'pending' : item.status,
    note: item.review_note,
    date: item.created_at,
    term: `${item.metric_result.academic_year} · HK${item.metric_result.semester}`,
  };
}
export function caseFromApi(item) {
  return {
    ...item,
    student: item.learner.id,
    owner: item.assigned_to == null ? 'Chưa phân công' : `Tài khoản #${item.assigned_to}`,
    date: item.created_at,
    followups: (item.followups || []).map((row) => ({
      ...row,
      date: row.performed_at,
      result: row.outcome,
      assessment: row.result_status,
      measurement: row.post_metric_result_id,
    })),
  };
}
