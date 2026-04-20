export function SourceTable({ rows, title }) {
  if (!rows?.length) {
    return (
      <section className="section-card">
        <h3>{title}</h3>
        <div className="empty-state">暂无可展示数据。</div>
      </section>
    );
  }

  const columns = Object.keys(rows[0]);

  return (
    <section className="section-card table-card">
      <h3>{title}</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${title}-${index}`}>
                {columns.map((column) => (
                  <td key={column}>{String(row[column] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
