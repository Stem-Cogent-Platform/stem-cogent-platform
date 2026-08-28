import Image from "next/image";

export function StemMark({ compact = false }: { compact?: boolean }) {
  return (
    <Image
      alt=""
      aria-hidden="true"
      className={compact ? "stem-logo stem-logo-compact" : "stem-logo"}
      height={compact ? 30 : 38}
      priority
      src="/stem-logo.png"
      width={compact ? 30 : 38}
    />
  );
}
