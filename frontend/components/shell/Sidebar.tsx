"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const primaryNav: NavItem[] = [
  {
    href: "/overview",
    label: "Overview",
    icon: (
      <svg className="sidebar__item-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1.5" y="1.5" width="5" height="5" rx="1" />
        <rect x="9.5" y="1.5" width="5" height="5" rx="1" />
        <rect x="1.5" y="9.5" width="5" height="5" rx="1" />
        <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
      </svg>
    ),
  },
  {
    href: "/obligations",
    label: "Obligations",
    icon: (
      <svg className="sidebar__item-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M2 4h12M2 8h8M2 12h10" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: "/recovery",
    label: "Recovery",
    icon: (
      <svg className="sidebar__item-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M8 2v4l2.5 2.5M14 8A6 6 0 1 1 2 8a6 6 0 0 1 12 0Z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    href: "/decisions",
    label: "Decisions",
    icon: (
      <svg className="sidebar__item-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="8" cy="8" r="6" />
        <path d="M8 5v3l2 2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    href: "/executions",
    label: "Executions",
    icon: (
      <svg className="sidebar__item-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M5.5 3L12 8l-6.5 5V3Z" strokeLinejoin="round" />
      </svg>
    ),
  },
];

const secondaryNav: NavItem[] = [
  {
    href: "/events",
    label: "Events",
    icon: (
      <svg className="sidebar__item-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M8 1v2M8 13v2M1 8H3M13 8h2" strokeLinecap="round" />
        <circle cx="8" cy="8" r="4" />
      </svg>
    ),
  },
  {
    href: "/policies",
    label: "Policies",
    icon: (
      <svg className="sidebar__item-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M8 1.5L2 4.5v4c0 3 2.5 5 6 6 3.5-1 6-3 6-6v-4L8 1.5Z" strokeLinejoin="round" />
      </svg>
    ),
  },
];

const sidebarListeners = new Set<() => void>();
const mobileMediaQuery = "(max-width: 600px)";

function subscribeToSidebarState(listener: () => void) {
  sidebarListeners.add(listener);
  return () => sidebarListeners.delete(listener);
}

function getSidebarState() {
  return window.localStorage.getItem("pulse-sidebar-collapsed") === "true";
}

function subscribeToMobileState(listener: () => void) {
  const mediaQuery = window.matchMedia(mobileMediaQuery);
  mediaQuery.addEventListener("change", listener);
  return () => mediaQuery.removeEventListener("change", listener);
}

function getMobileState() {
  return window.matchMedia(mobileMediaQuery).matches;
}

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useSyncExternalStore(
    subscribeToSidebarState,
    getSidebarState,
    () => false
  );
  const isMobile = useSyncExternalStore(
    subscribeToMobileState,
    getMobileState,
    () => false
  );
  const isCollapsed = collapsed && !isMobile;

  function toggleCollapsed() {
    window.localStorage.setItem("pulse-sidebar-collapsed", String(!collapsed));
    sidebarListeners.forEach((listener) => listener());
  }

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <aside className={`sidebar${isCollapsed ? " sidebar--collapsed" : ""}`} role="navigation" aria-label="Main navigation">
      <div className="sidebar__header">
        <div className="sidebar__logo" aria-hidden="true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1L12 4.5V9.5L7 13L2 9.5V4.5L7 1Z" fill="white" fillOpacity="0.9" />
          </svg>
        </div>
        <span className="sidebar__wordmark">
          Pulse<span>.</span>
        </span>
        <button
          type="button"
          className="sidebar__toggle"
          onClick={toggleCollapsed}
          aria-label={isCollapsed ? "Expand navigation" : "Collapse navigation"}
          aria-expanded={!isCollapsed}
          title={isCollapsed ? "Expand navigation" : "Collapse navigation"}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d={isCollapsed ? "m6 3 5 5-5 5" : "m10 3-5 5 5 5"} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <div className="sidebar__body">
        <div className="sidebar__nav-group">
          <p className="sidebar__section-label">Platform</p>
          {primaryNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar__item${isActive(item.href) ? " sidebar__item--active" : ""}`}
              aria-current={isActive(item.href) ? "page" : undefined}
              title={isCollapsed ? item.label : undefined}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </div>
        <div className="sidebar__nav-group sidebar__nav-group--secondary">
          <p className="sidebar__section-label">System</p>
          {secondaryNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar__item${isActive(item.href) ? " sidebar__item--active" : ""}`}
              aria-current={isActive(item.href) ? "page" : undefined}
              title={isCollapsed ? item.label : undefined}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="sidebar__footer">
        <div className="env-badge">
          <span className="env-badge__dot" aria-hidden="true" />
          Test Mode
        </div>
      </div>
    </aside>
  );
}
