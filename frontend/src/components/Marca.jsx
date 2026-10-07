export default function Marca({ width = 26, height = 26, className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width={width}
      height={height}
      aria-hidden="true"
      focusable="false"
    >
      <path d="M12 2.5c4.6 5.2 4.6 11.6 0 19-4.6-7.4-4.6-13.8 0-19Z" fill="currentColor" />
      <path
        d="M12 7v10"
        stroke="var(--bosque)"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  )
}
