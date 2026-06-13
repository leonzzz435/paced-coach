import { renderToString } from "react-dom/server";

import HtmlSnippet from "../../components/html_snippet";

function assertCondition(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function run(): void {
  const payload = `<script>alert("xss")</script><p>safe text</p><img src="x" onerror="alert('xss')" />`;
  const rendered = renderToString(<HtmlSnippet html={payload} className="probe" />);

  assertCondition(!rendered.includes("<script"), "SSR output must not include script tags");
  assertCondition(!rendered.toLowerCase().includes("onerror="), "SSR output must not include event handlers");
  assertCondition(!rendered.includes("safe text"), "SSR output must not render raw HTML payload");

  console.log("HtmlSnippet SSR safety check passed.");
}

run();
