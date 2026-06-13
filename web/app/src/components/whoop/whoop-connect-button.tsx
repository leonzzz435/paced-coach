import WhoopPuck from "@/components/whoop/whoop-puck";

type WhoopConnectButtonProps = {
  enabled: boolean;
  href: string;
  className?: string;
};

export default function WhoopConnectButton({ enabled, href, className }: WhoopConnectButtonProps) {
  const baseClassName =
    "inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium shadow-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2";
  const buttonClassName = `${baseClassName} bg-[#00F19F] text-black hover:bg-[#00D98F] focus-visible:outline-black ${
    enabled ? "" : "cursor-not-allowed opacity-60 hover:bg-[#00F19F]"
  }`;

  if (!enabled) {
    return (
      <button
        className={`${buttonClassName} ${className ?? ""}`}
        disabled
        type="button"
        title="WHOOP OAuth is disabled or not configured."
      >
        <WhoopPuck className="h-[30px] w-[30px]" variant="black" />
        <span>Connect WHOOP</span>
      </button>
    );
  }

  return (
    <a className={`${buttonClassName} ${className ?? ""}`} href={href}>
      <WhoopPuck className="h-[30px] w-[30px]" variant="black" />
      <span>Connect WHOOP</span>
    </a>
  );
}
