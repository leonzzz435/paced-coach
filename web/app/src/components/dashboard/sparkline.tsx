import { useId } from "react";

type Props = {
  points: number[];
  width?: number;
  height?: number;
  color?: string;
  statusColor?: string;
};

export default function Sparkline({ points, width = 72, height = 22, color = "#18181b", statusColor }: Props) {
  const uniqueId = useId();
  if (!points || points.length < 2) return null;

  const stroke = statusColor ?? color;
  const padding = 2;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = Math.max(1e-9, max - min);

  const coords = points.map((value, index) => {
    const x = padding + (index * (width - padding * 2)) / (points.length - 1);
    const y = padding + ((max - value) * (height - padding * 2)) / span;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  const linePoints = coords.join(" ");
  const fillPoints = `${linePoints} ${width - padding},${height - padding} ${padding},${height - padding}`;
  const gradientId = `spark-${uniqueId.replace(/[^a-z0-9]+/gi, "")}`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={fillPoints} fill={`url(#${gradientId})`} />
      <polyline points={linePoints} fill="none" stroke={stroke} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
