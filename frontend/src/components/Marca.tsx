export default function Marca({ claro = false }: { claro?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 px-1">
      <svg viewBox="0 0 40 40" className="h-8 w-8" aria-hidden="true">
        <rect width="40" height="40" rx="10" fill={claro ? "#ffffff14" : "#10201A"} />
        <path fill="#1FB37A" d="M7 10h26l-3.4 7.4H10.4z" />
        <path fill={claro ? "#E8F3EE" : "#E8F3EE"} d="M12 20.4h16l-2.9 6.3h-10.2z" />
        <path fill="#E0428F" d="M16.4 29.6h7.2L20 35z" />
      </svg>
      <span className={"font-titulo text-xl font-semibold tracking-tight " + (claro ? "text-white" : "text-tinta")}>
        StoneFalcon
      </span>
    </div>
  );
}
