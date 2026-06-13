"use client";

import DOMPurify from "dompurify";
import { useMemo } from "react";

type Props = {
  html: string;
  className?: string;
};

type PurifyConfig = Parameters<typeof DOMPurify.sanitize>[1];

const PURIFY_CONFIG: PurifyConfig = {
  ALLOWED_TAGS: [
    "div", "span", "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "strong", "em", "b", "i", "small", "blockquote",
    "label", "input",
    "a",
  ],
  ALLOWED_ATTR: [
    "class", "id", "style",
    "type", "checked",
    "href", "target", "rel",
    "rowspan", "colspan",
  ],
  ALLOW_DATA_ATTR: false,
};

function normalizeHeaderLabel(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function classifyHeaderLabel(label: string): "primary" | "meta" | "badge" | "detail" | null {
  const normalized = normalizeHeaderLabel(label);

  if (!normalized) return null;
  if (/(^| )(priority|status)( |$)/.test(normalized)) return "badge";
  if (/(^| )(date|day|days|latest|current)( |$)/.test(normalized)) return "meta";
  if (/(^| )(note|notes|details|detail|role|goal|meaning|signal|direction)( |$)/.test(normalized)) {
    return "detail";
  }
  if (/(^| )(race|event|domain|metric|kpi|checkpoint)( |$)/.test(normalized)) return "primary";

  return null;
}

function enhanceSanitizedHtml(html: string): string {
  if (!html.trim()) return "";

  const parser = new DOMParser();
  const doc = parser.parseFromString(`<body>${html}</body>`, "text/html");
  const body = doc.body;

  body.querySelectorAll("table").forEach((table) => {
    const headerLabels = Array.from(table.querySelectorAll("thead th")).map((header) =>
      header.textContent?.trim() ?? "",
    );

    if (headerLabels.length === 0) return;

    table.classList.add("table--enhanced");

    table.querySelectorAll("tbody tr").forEach((row) => {
      let hasPrimary = false;
      let hasDetail = false;

      Array.from(row.querySelectorAll("td")).forEach((cell, index) => {
        const label = headerLabels[index] ?? `Column ${index + 1}`;
        cell.setAttribute("data-label", label);

        const semanticRole = classifyHeaderLabel(label);
        if (!semanticRole) return;

        cell.classList.add(`cell--${semanticRole}`);
        if (semanticRole === "primary") hasPrimary = true;
        if (semanticRole === "detail") hasDetail = true;
      });

      if (hasPrimary) row.classList.add("table-row--with-primary");
      if (hasDetail) row.classList.add("table-row--with-detail");
    });
  });

  return body.innerHTML;
}

export default function HtmlSnippet({ html, className }: Props) {
  const safeHtml = useMemo(() => {
    if (typeof window === "undefined") return "";

    const sanitized = DOMPurify.sanitize(html, PURIFY_CONFIG);
    return enhanceSanitizedHtml(sanitized);
  }, [html]);

  return (
    <div
      className={className}
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: safeHtml }}
    />
  );
}
