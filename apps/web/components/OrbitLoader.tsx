/** The app's orbit mark, animated — used everywhere something is loading so
 *  a wait reads as "Orrery is working" rather than a generic spinner. */
export default function OrbitLoader({ size = 40 }: { size?: number }) {
  return (
    <svg
      className="orbit-loader"
      width={size}
      height={size}
      viewBox="0 0 44 44"
      role="status"
      aria-label="Loading"
    >
      <ellipse
        className="orbit-ring orbit-ring-a"
        cx="22"
        cy="22"
        rx="20"
        ry="9"
        stroke="#5aa9c7"
        strokeWidth="2.2"
        fill="none"
      />
      <ellipse
        className="orbit-ring orbit-ring-b"
        cx="22"
        cy="22"
        rx="20"
        ry="9"
        stroke="#4bd6b0"
        strokeWidth="2.2"
        fill="none"
        transform="rotate(60 22 22)"
      />
      <ellipse
        className="orbit-ring orbit-ring-c"
        cx="22"
        cy="22"
        rx="20"
        ry="9"
        stroke="#e0b341"
        strokeWidth="2.2"
        fill="none"
        transform="rotate(120 22 22)"
      />
      <circle cx="22" cy="22" r="5" fill="#e6eef5" />
    </svg>
  );
}
