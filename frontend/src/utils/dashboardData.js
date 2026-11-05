// Dùng chung cho dashboard và báo cáo để không lệch phạm vi, trạng thái.
export function dashboardData(students, alerts, cases) {
  const studying = students.filter((student) => student.status === 'studying');
  const ids = new Set(studying.map((student) => student.id));
  const scopedAlerts = alerts.filter((alert) => ids.has(alert.student));
  const pendingAlerts = scopedAlerts.filter((alert) => alert.status === 'pending');
  const scopedCases = cases.filter((item) => ids.has(item.student));
  return {
    students: studying,
    alerts: scopedAlerts,
    pendingAlerts,
    cases: scopedCases,
    openCases: scopedCases.filter((item) => item.status !== 'closed'),
  };
}

export function reportRows(students, alerts, cases, isDashboard) {
  const scope = isDashboard
    ? dashboardData(students, alerts, cases)
    : { students, alerts, cases };
  const reportAlerts = isDashboard ? scope.pendingAlerts : scope.alerts;
  const reportCases = isDashboard ? scope.openCases : scope.cases;
  return [
    [
      'Mã sinh viên',
      'Họ tên',
      'Chương trình',
      'Khóa',
      isDashboard ? 'Cảnh báo chờ rà soát' : 'Tổng cảnh báo',
      isDashboard ? 'Hồ sơ hỗ trợ chưa đóng' : 'Tổng hồ sơ hỗ trợ',
    ],
    ...scope.students.map((student) => [
      student.id,
      student.name,
      student.program,
      student.cohort,
      reportAlerts.filter((alert) => alert.student === student.id).length,
      reportCases.filter((item) => item.student === student.id).length,
    ]),
  ];
}
