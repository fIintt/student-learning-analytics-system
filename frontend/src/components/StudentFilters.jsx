import { Search } from 'lucide-react';
export default function StudentFilters({
  searchQuery,
  setSearchQuery,
  selectedProgram,
  setSelectedProgram,
  database,
  accessibleStudents,
  selectedGroup,
  setSelectedGroup,
  groups,
}) {
  return (
    <div className="filters">
      <div className="search">
        <Search size={16} />
        <input
          aria-label="Tìm sinh viên"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Tìm tên hoặc mã sinh viên…"
        />
      </div>
      <select
        aria-label="Chương trình"
        value={selectedProgram}
        onChange={(event) => setSelectedProgram(event.target.value)}
      >
        <option value="all">Tất cả chương trình</option>
        {database.programs
          .filter((program) =>
            accessibleStudents.some((student) => student.program === program.id),
          )
          .map((program) => (
            <option key={program.id} value={program.id}>
              {program.id} · {program.name}
            </option>
          ))}
      </select>
      <select
        aria-label="Nhóm"
        value={selectedGroup}
        onChange={(event) => setSelectedGroup(event.target.value)}
      >
        <option value="all">Tất cả nhóm</option>
        {groups.map((group) => (
          <option key={group}>{group}</option>
        ))}
      </select>
    </div>
  );
}
