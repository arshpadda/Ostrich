import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

// Lazy-loaded on demand (see MessageBubble) so react-syntax-highlighter — the
// single largest dependency — is split out of the main bundle.
export default function CodeBlock({ language, value }: { language: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };
  return (
    <div className="group relative my-2">
      <button
        onClick={copy}
        className="absolute right-2 top-2 z-10 rounded bg-white/10 px-2 py-0.5 text-[10px] text-zinc-300 opacity-0 transition group-hover:opacity-100"
      >
        {copied ? "Copied" : "Copy"}
      </button>
      <SyntaxHighlighter language={language} style={oneDark} PreTag="div" customStyle={{ margin: 0, borderRadius: 8, fontSize: 13 }}>
        {value}
      </SyntaxHighlighter>
    </div>
  );
}
