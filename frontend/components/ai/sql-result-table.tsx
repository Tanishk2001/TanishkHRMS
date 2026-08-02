export default function SqlResultTable({ rows, sql }: { rows: Record<string, unknown>[]; sql: string | null }) {
  if (!rows.length) {
    return <p className="text-sm text-muted mt-2">No matching records were found.</p>;
  }
  const columns = Object.keys(rows[0]);

  return (
    <div className="mt-3 space-y-2">
      {sql && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer select-none">View generated SQL</summary>
          <pre className="mt-1 p-2 bg-base border border-border text-ink rounded overflow-x-auto font-mono">{sql.trim()}</pre>
        </details>
      )}
      <div className="overflow-x-auto border border-border rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-base">
            <tr>
              {columns.map((c) => (
                <th key={c} className="text-left font-medium text-muted px-3 py-2 whitespace-nowrap font-mono text-xs">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-border">
                {columns.map((c) => (
                  <td key={c} className="px-3 py-2 whitespace-nowrap text-ink">
                    {String(row[c] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
