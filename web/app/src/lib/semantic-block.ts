import type { SemanticBlockV3 } from "@/components/plan-viewer/types";

export function semanticBlockTitle(block: SemanticBlockV3): string | null {
  if (block.type === "disclosure") return block.label;
  return block.title ?? null;
}

export function semanticBlockText(block: SemanticBlockV3): string {
  switch (block.type) {
    case "narrative":
    case "callout":
    case "recovery":
    case "notes":
      return block.markdown;
    case "workout":
      return `${block.title}: ${block.objective_markdown}`;
    case "interval_table":
      return block.intervals.map((row) => `${row.label}: ${row.duration} ${row.prescription}`).join("; ");
    case "fueling":
      return [block.before_markdown, block.during_markdown, block.after_markdown].filter(Boolean).join(" ");
    case "checklist":
      return block.items.map((item) => item.label).join("; ");
    case "data_table":
      return block.rows.map((row) => Object.values(row).join(" · ")).join("; ");
    case "phase_timeline":
      return block.milestones.map((milestone) => milestone.label).join(" → ");
    case "disclosure":
      return block.summary_markdown;
  }
}
