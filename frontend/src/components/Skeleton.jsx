// Skeleton.jsx
// Simple placeholder blocks shown while data is loading.
// They shimmer instead of leaving a blank screen.

function Skeleton({ className = "" }) {
  return <div className={`skeleton ${className}`} />;
}

// A full card-shaped skeleton (used on the dashboard / history pages).
export function SkeletonCard() {
  return (
    <div className="card">
      <Skeleton className="sk-line" style={{ width: "40%" }} />
      <Skeleton className="sk-line" style={{ width: "70%" }} />
      <Skeleton className="sk-line" style={{ width: "90%" }} />
      <Skeleton className="sk-line" style={{ width: "55%" }} />
    </div>
  );
}

export default Skeleton;