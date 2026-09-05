import type { ReactNode } from "react";

import { LogIcon, OverviewIcon, UsersIcon } from "./Icons";

export type Section = "overview" | "clients" | "journal";

const navigation = [
  { id: "overview" as const, label: "Обзор", icon: OverviewIcon },
  { id: "clients" as const, label: "Клиенты", icon: UsersIcon },
  { id: "journal" as const, label: "Журнал", icon: LogIcon },
];

export function AppShell({
  activeSection,
  onSectionChange,
  children,
}: {
  activeSection: Section;
  onSectionChange: (section: Section) => void;
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Основная навигация">
        <div className="brand" aria-label="Amnezia Control Panel">AMN</div>
        <nav className="main-nav">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              className="nav-item"
              data-active={activeSection === id}
              key={id}
              onClick={() => onSectionChange(id)}
              type="button"
            >
              <Icon size={20} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </aside>
      {children}
    </div>
  );
}
