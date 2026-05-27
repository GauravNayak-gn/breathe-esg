export default function StatusBadge({ status }) {
  const badgeClass = `badge badge-${status.toLowerCase()}`;
  return (
    <span className={badgeClass}>
      {status}
    </span>
  );
}
