"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ComponentPropsWithoutRef } from "react";

/**
 * Shared Markdown renderer for the Stem Decision Copilot.
 * Renders structured markdown with GFM tables, lists, and styled headings.
 * Used by the Copilot chat feed and the Working Canvas.
 */
export function MarkdownRenderer({ content, className = "" }: { content: string; className?: string }) {
  return (
    <div className={`prose prose-slate prose-sm max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (props: ComponentPropsWithoutRef<"h1">) => (
            <h1 className="text-lg font-black tracking-tight text-slate-900 mt-5 mb-3 pb-2 border-b border-slate-200" {...props} />
          ),
          h2: (props: ComponentPropsWithoutRef<"h2">) => (
            <h2 className="text-base font-bold text-slate-900 mt-5 mb-2 pb-1.5 border-b border-slate-100" {...props} />
          ),
          h3: (props: ComponentPropsWithoutRef<"h3">) => (
            <h3 className="text-sm font-bold text-slate-800 mt-4 mb-1.5" {...props} />
          ),
          p: (props: ComponentPropsWithoutRef<"p">) => (
            <p className="text-sm text-slate-700 leading-relaxed my-2" {...props} />
          ),
          ul: (props: ComponentPropsWithoutRef<"ul">) => (
            <ul className="list-disc pl-5 space-y-1.5 my-3 text-sm text-slate-700" {...props} />
          ),
          ol: (props: ComponentPropsWithoutRef<"ol">) => (
            <ol className="list-decimal pl-5 space-y-1.5 my-3 text-sm text-slate-700" {...props} />
          ),
          li: (props: ComponentPropsWithoutRef<"li">) => (
            <li className="text-sm leading-relaxed" {...props} />
          ),
          strong: (props: ComponentPropsWithoutRef<"strong">) => (
            <strong className="font-bold text-slate-900" {...props} />
          ),
          blockquote: (props: ComponentPropsWithoutRef<"blockquote">) => (
            <blockquote className="border-l-3 border-blue-300 bg-blue-50/50 pl-4 py-2 my-3 text-sm text-slate-700 italic rounded-r-lg" {...props} />
          ),
          hr: () => <hr className="my-5 border-slate-200" />,
          table: (props: ComponentPropsWithoutRef<"table">) => (
            <div className="overflow-x-auto my-4 rounded-lg border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-xs" {...props} />
            </div>
          ),
          thead: (props: ComponentPropsWithoutRef<"thead">) => (
            <thead className="bg-slate-50" {...props} />
          ),
          th: (props: ComponentPropsWithoutRef<"th">) => (
            <th className="px-3 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-slate-600" {...props} />
          ),
          td: (props: ComponentPropsWithoutRef<"td">) => (
            <td className="px-3 py-2 border-t border-slate-100 text-sm text-slate-700" {...props} />
          ),
          a: (props: ComponentPropsWithoutRef<"a">) => (
            <a className="text-blue-700 font-medium underline hover:text-blue-800" target="_blank" rel="noreferrer" {...props} />
          ),
          code: ({ className: codeClass, children, ...props }: ComponentPropsWithoutRef<"code"> & { children?: React.ReactNode }) => {
            const isBlock = codeClass?.includes("language-");
            if (isBlock) {
              return (
                <pre className="rounded-lg bg-slate-900 text-slate-100 p-4 overflow-x-auto my-3 text-xs leading-relaxed">
                  <code className={codeClass} {...props}>{children}</code>
                </pre>
              );
            }
            return (
              <code className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
