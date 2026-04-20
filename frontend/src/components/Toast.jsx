export default function Toast({ toast }) {
  return <div className={`toast ${toast.visible ? "visible" : "hidden"} ${toast.tone || ""}`.trim()}>{toast.message}</div>;
}
