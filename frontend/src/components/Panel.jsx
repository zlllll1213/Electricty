export default function Panel({ kicker, title, note, children }) {
  return (
    <section className="panel">
      <div className="panel-head">
        {kicker ? <p className="panel-kicker">{kicker}</p> : null}
        <h3 className="panel-title">{title}</h3>
        {note ? <p className="panel-note">{note}</p> : null}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}
