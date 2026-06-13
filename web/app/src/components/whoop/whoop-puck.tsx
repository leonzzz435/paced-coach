import Image from "next/image";

type WhoopPuckVariant = "black" | "white";

type WhoopPuckProps = {
  variant?: WhoopPuckVariant;
  size?: number;
  className?: string;
  alt?: string;
};

export default function WhoopPuck({
  variant = "black",
  size = 30,
  className,
  alt = "WHOOP",
}: WhoopPuckProps) {
  return (
    <Image
      src={`/brands/whoop/whoop-puck-${variant}.svg`}
      width={size}
      height={size}
      className={className}
      alt={alt}
      unoptimized
    />
  );
}
