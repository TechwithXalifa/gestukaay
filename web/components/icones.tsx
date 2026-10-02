/** Icônes au trait (type Lucide, 9.6) et logo baobab. Toujours décoratives : aria-hidden. */
type P = { taille?: number };

function Ic({ taille = 20, children }: P & { children: React.ReactNode }) {
  return (
    <svg className="ic" viewBox="0 0 24 24" width={taille} height={taille} aria-hidden="true">
      {children}
    </svg>
  );
}

export const Baobab = () => (
  <svg viewBox="0 -0.5 33 43" width={23} height={30} aria-hidden="true" className="baobab">
    <path
      className="bb"
      d="M16 20.7V36.4M16 36.4 10.8 40.8M16 36.4 21.3 40.8M16 20.7 2.9 12M16 20.7 10.5 4.2M16 20.7 18.2 2.1M16 20.7 25.8 5.3M16 20.7 30.2 14.1"
    />
    <g fill="currentColor">
      <circle cx="2.9" cy="12" r="2.3" /><circle cx="10.5" cy="4.2" r="2.3" />
      <circle cx="18.2" cy="2.1" r="2.3" /><circle cx="25.8" cy="5.3" r="2.3" />
      <circle cx="30.2" cy="14.1" r="2.3" />
    </g>
  </svg>
);

export const Coche = (p: P) => <Ic {...p}><path d="M20 6 9 17l-5-5" /></Ic>;
export const Info = (p: P) => <Ic {...p}><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></Ic>;
export const Livre = (p: P) => (
  <Ic {...p}><path d="M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z" /><path d="M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z" /></Ic>
);
export const Copier = (p: P) => (
  <Ic {...p}><rect width="13" height="13" x="9" y="9" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></Ic>
);
export const Partager = (p: P) => (
  <Ic {...p}><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4" /></Ic>
);
export const Fleche = (p: P) => <Ic {...p}><path d="M5 12h14M12 5l7 7-7 7" /></Ic>;
export const Externe = (p: P) => <Ic {...p}><path d="M7 7h10v10M7 17 17 7" /></Ic>;
export const Drapeau = (p: P) => (
  <Ic {...p}><path d="M4 22V4M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1" /></Ic>
);
export const Pouce = ({ bas, ...p }: P & { bas?: boolean }) => (
  <Ic {...p}>
    <g transform={bas ? "rotate(180 12 12)" : undefined}>
      <path d="M7 10v12M15 5.9 14 10h5.8a2 2 0 0 1 1.9 2.6l-2.3 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.8a2 2 0 0 0 1.8-1.1L12 2a3.1 3.1 0 0 1 3 3.9Z" />
    </g>
  </Ic>
);
export const Base = (p: P) => (
  <Ic {...p}><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v14a9 3 0 0 0 18 0V5M3 12a9 3 0 0 0 18 0" /></Ic>
);
export const Tourne = ({ taille = 20 }: P) => (
  <svg className="ic spin" viewBox="0 0 24 24" width={taille} height={taille} aria-hidden="true">
    <path d="M21 12a9 9 0 1 1-6.2-8.6" />
  </svg>
);
export const Telecharger = (p: P) => <Ic {...p}><path d="M12 15V3M6 9l6 6 6-6M19 21H5" /></Ic>;
export const Micro = (p: P) => (
  <Ic {...p}><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3" /></Ic>
);
export const MicroBarre = (p: P) => (
  <Ic {...p}><path d="m2 2 20 20M18.9 13a7 7 0 0 0 .1-1v-2M5 10v2a7 7 0 0 0 12 5M15 9.3V5a3 3 0 0 0-5.7-1.3M9 9v3a3 3 0 0 0 5.1 2.1M12 19v3" /></Ic>
);
export const Cadenas = (p: P) => (
  <Ic {...p}><rect width="18" height="11" x="3" y="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></Ic>
);
export const Wifi = (p: P) => (
  <Ic {...p}><path d="M12 20h.01M8.5 16.4a5 5 0 0 1 7 0M5 12.9a10 10 0 0 1 5.2-2.8M19 12.9a10 10 0 0 0-2.2-1.6M2 8.8a15 15 0 0 1 4.2-2.6M22 8.8a15 15 0 0 0-11.3-3.7M2 2l20 20" /></Ic>
);
export const Chevron = (p: P) => <Ic {...p}><path d="m15 18-6-6 6-6" /></Ic>;
