"use client";

import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

type Props = {
  markdown: string;
  className?: string;
};

function joinClassNames(...names: Array<string | undefined>): string {
  return names.filter(Boolean).join(" ");
}

export default function MarkdownSnippet({ markdown, className }: Props) {
  const source = markdown.trim();
  if (!source) return null;

  return (
    <div className={joinClassNames("md-snippet", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          h1: ({ children }) => <h3 className="mt-2 text-sm font-semibold leading-snug first:mt-0">{children}</h3>,
          h2: ({ children }) => <h3 className="mt-2 text-sm font-semibold leading-snug first:mt-0">{children}</h3>,
          h3: ({ children }) => <h4 className="mt-2 text-sm font-semibold leading-snug first:mt-0">{children}</h4>,
          p: ({ children }) => <p className="mt-2 leading-relaxed first:mt-0">{children}</p>,
          ul: ({ children }) => <ul className="mt-2 list-disc space-y-1 pl-5 first:mt-0">{children}</ul>,
          ol: ({ children }) => <ol className="mt-2 list-decimal space-y-1 pl-5 first:mt-0">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="mt-2 border-l-2 border-zinc-300 pl-3 text-zinc-700 first:mt-0">
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => (
            <a
              className="underline decoration-zinc-400 underline-offset-2 hover:decoration-zinc-700"
              href={href}
              rel="noreferrer noopener"
              target="_blank"
            >
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="rounded bg-zinc-200/80 px-1 py-0.5 font-mono text-[0.85em] text-zinc-900">{children}</code>
          ),
          pre: ({ children }) => (
            <pre className="mt-2 overflow-x-auto rounded-lg bg-zinc-900 p-3 text-xs text-zinc-100 first:mt-0">{children}</pre>
          ),
          hr: () => <hr className="my-3 border-zinc-200" />,
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
