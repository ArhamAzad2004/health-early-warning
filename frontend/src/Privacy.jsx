export default function Privacy({ roles }) {
  return (
    <div className="privacy">
      <section className="card">
        <h2>Privacy by design</h2>
        <ul>
          <li><strong>Aggregated only.</strong> The system stores daily counts per district or work site. No individual records exist, so none can be shown.</li>
          <li><strong>Small-cell suppression.</strong> Any health or workforce count from 1 to 4 is shown as “&lt;5”, so no one can be singled out.</li>
          <li><strong>Role-based views.</strong> Each role sees only what its job needs (table below).</li>
          <li><strong>Hard boundary.</strong> Outputs are for prevention planning. They must not be used for decisions about any individual’s employment, pay or discipline.</li>
          <li><strong>Explainable.</strong> Every alert shows its evidence, assumptions and data completeness, so it can be challenged.</li>
        </ul>
      </section>
      <section className="card">
        <h2>Who sees what</h2>
        <table>
          <thead><tr><th>Role</th><th>Districts</th><th>Work sites</th><th>Health counts</th><th>Validation</th></tr></thead>
          <tbody>
            <tr><td>{roles.public_health}</td><td>All</td><td>All (aggregated)</td><td>Yes, suppressed &lt;5</td><td>Yes</td></tr>
            <tr><td>{roles.employer_hse}</td><td>–</td><td>Own sites only</td><td>Own sites, suppressed &lt;5</td><td>Yes</td></tr>
            <tr><td>{roles.public}</td><td>All</td><td>–</td><td>No: weather, air quality and advisories</td><td>No</td></tr>
          </tbody>
        </table>
      </section>
    </div>
  )
}
