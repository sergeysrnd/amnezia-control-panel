import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function IconBase({ size = 20, children, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      {...props}
    >
      {children}
    </svg>
  );
}

const strokeProps = {
  stroke: "currentColor",
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  strokeWidth: 1.75,
};

export function OverviewIcon(props: IconProps) {
  return <IconBase {...props}><rect {...strokeProps} height="13" rx="1.8" width="18" x="3" y="4" /><path {...strokeProps} d="M8 21h8M12 17v4" /></IconBase>;
}

export function UsersIcon(props: IconProps) {
  return <IconBase {...props}><path {...strokeProps} d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></IconBase>;
}

export function LogIcon(props: IconProps) {
  return <IconBase {...props}><path {...strokeProps} d="M6 3h9l4 4v14H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path {...strokeProps} d="M14 3v5h5M8 13h7M8 17h7" /></IconBase>;
}

export function RefreshIcon(props: IconProps) {
  return <IconBase {...props}><path {...strokeProps} d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7" /></IconBase>;
}

export function PlusIcon(props: IconProps) {
  return <IconBase {...props}><path {...strokeProps} d="M12 5v14M5 12h14" /></IconBase>;
}

export function CloseIcon(props: IconProps) {
  return <IconBase {...props}><path {...strokeProps} d="m6 6 12 12M18 6 6 18" /></IconBase>;
}

export function CopyIcon(props: IconProps) {
  return <IconBase {...props}><rect {...strokeProps} height="13" rx="2" width="13" x="8" y="8" /><path {...strokeProps} d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></IconBase>;
}

export function DownloadIcon(props: IconProps) {
  return <IconBase {...props}><path {...strokeProps} d="M12 3v12m0 0 4-4m-4 4-4-4M4 20h16" /></IconBase>;
}

export function TrashIcon(props: IconProps) {
  return <IconBase {...props}><path {...strokeProps} d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6M10 10v7M14 10v7" /></IconBase>;
}

export function SortIcon({ direction = "none", ...props }: IconProps & { direction?: "asc" | "desc" | "none" }) {
  const path = direction === "asc" ? "m8 14 4-4 4 4" : direction === "desc" ? "m8 10 4 4 4-4" : "m9 8 3-3 3 3m0 8-3 3-3-3";
  return <IconBase size={14} {...props}><path {...strokeProps} d={path} /></IconBase>;
}

export function CheckIcon(props: IconProps) {
  return <IconBase {...props}><circle {...strokeProps} cx="12" cy="12" r="9" /><path {...strokeProps} d="m8 12 2.5 2.5L16 9" /></IconBase>;
}

export function WarningIcon(props: IconProps) {
  return <IconBase {...props}><path {...strokeProps} d="M10.3 3.8 2.5 18a2 2 0 0 0 1.75 3h15.5a2 2 0 0 0 1.75-3L13.7 3.8a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01" /></IconBase>;
}

