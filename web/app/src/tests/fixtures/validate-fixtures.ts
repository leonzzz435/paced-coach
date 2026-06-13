import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { DEFAULT_DEMO_PERSONA_ID, DEMO_PERSONA_IDS, resolveDemoPersonaId, type DemoPersonaId } from "@/lib/demo/personas";
import { SUPPORTED_SCHEMA_VERSIONS } from "@/lib/generated/version-manifest";
import type {
  UiAnalysis,
  UiDisclosureNode,
  UiHtmlBlock,
  UiSeasonPhase,
  UiSeasonPlan,
  UiWeekPlan,
  UiWeeklyPlan,
} from "@/lib/types/ui-blocks";

function assertCondition(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function assertString(value: unknown, label: string): void {
  assertCondition(typeof value === "string" && value.length > 0, `${label} must be a non-empty string`);
}

function assertArray<T>(value: unknown, label: string): T[] {
  assertCondition(Array.isArray(value), `${label} must be an array`);
  return value as T[];
}

function assertHtmlBlock(block: UiHtmlBlock, path: string): void {
  assertCondition(block.type === "html", `${path}.type must be "html"`);
  assertString(block.key, `${path}.key`);
  assertString(block.content_html, `${path}.content_html`);
  assertCondition(Boolean(block.variant), `${path}.variant must be set`);
}

function validateDisclosureNodes(nodes: UiDisclosureNode[] | undefined, path: string): void {
  if (!nodes) {
    return;
  }
  assertCondition(Array.isArray(nodes), `${path} must be an array when provided`);
  nodes.forEach((node, idx) => {
    assertString(node.node_id, `${path}[${idx}].node_id`);
    assertString(node.title, `${path}[${idx}].title`);
    if (node.disclosure_mode !== undefined) {
      assertCondition(
        node.disclosure_mode === "auto" || node.disclosure_mode === "collapsible" || node.disclosure_mode === "inline",
        `${path}[${idx}].disclosure_mode must be auto|collapsible|inline`,
      );
    }
    assertArray<UiHtmlBlock>(node.blocks, `${path}[${idx}].blocks`).forEach((block, blockIdx) => {
      assertHtmlBlock(block, `${path}[${idx}].blocks[${blockIdx}]`);
    });
    validateDisclosureNodes(node.children, `${path}[${idx}].children`);
  });
}

function validateAnalysis(analysis: UiAnalysis): void {
  assertCondition(analysis.type === "analysis", "analysis.type must be 'analysis'");
  assertCondition(analysis.schema_version > 0, "analysis.schema_version must be > 0");
  assertString(analysis.analysis_id, "analysis.analysis_id");
  assertString(analysis.athlete_name, "analysis.athlete_name");
  if (analysis.dashboard_kpis) {
    assertArray(analysis.dashboard_kpis, "analysis.dashboard_kpis");
    analysis.dashboard_kpis.forEach((kpi, idx) => {
      assertString(kpi.kpi_id, `analysis.dashboard_kpis[${idx}].kpi_id`);
      assertString(kpi.label, `analysis.dashboard_kpis[${idx}].label`);
      assertString(kpi.value, `analysis.dashboard_kpis[${idx}].value`);
      assertCondition(Boolean(kpi.status), `analysis.dashboard_kpis[${idx}].status must be set`);
    });
  }
  assertArray(analysis.kpis, "analysis.kpis");
  assertArray(analysis.sections, "analysis.sections");

  analysis.kpis.forEach((kpi, idx) => {
    assertString(kpi.kpi_id, `analysis.kpis[${idx}].kpi_id`);
    assertString(kpi.label, `analysis.kpis[${idx}].label`);
    assertString(kpi.value, `analysis.kpis[${idx}].value`);
    assertCondition(Boolean(kpi.status), `analysis.kpis[${idx}].status must be set`);
  });

  analysis.sections.forEach((section, idx) => {
    assertString(section.section_id, `analysis.sections[${idx}].section_id`);
    assertString(section.title, `analysis.sections[${idx}].title`);
    assertCondition(Boolean(section.tone), `analysis.sections[${idx}].tone must be set`);
    assertArray<UiHtmlBlock>(section.blocks, `analysis.sections[${idx}].blocks`).forEach((block, blockIdx) => {
      assertHtmlBlock(block, `analysis.sections[${idx}].blocks[${blockIdx}]`);
    });
    validateDisclosureNodes(section.nodes, `analysis.sections[${idx}].nodes`);
  });
}

function validateSeasonPlan(plan: UiSeasonPlan): void {
  assertCondition(plan.type === "season_plan", "season_plan.type must be 'season_plan'");
  assertCondition(plan.schema_version > 0, "season_plan.schema_version must be > 0");
  assertString(plan.plan_id, "season_plan.plan_id");
  assertString(plan.athlete_name, "season_plan.athlete_name");
  assertString(plan.start_date, "season_plan.start_date");
  assertString(plan.end_date, "season_plan.end_date");

  const phases = assertArray<UiSeasonPhase>(plan.phases, "season_plan.phases");
  validateDisclosureNodes(plan.global_nodes, "season_plan.global_nodes");
  phases.forEach((phase, idx) => {
    assertString(phase.phase_id, `season_plan.phases[${idx}].phase_id`);
    assertString(phase.title, `season_plan.phases[${idx}].title`);
    assertString(phase.start_date, `season_plan.phases[${idx}].start_date`);
    assertString(phase.end_date, `season_plan.phases[${idx}].end_date`);
    assertArray<UiHtmlBlock>(phase.blocks, `season_plan.phases[${idx}].blocks`).forEach((block, blockIdx) => {
      assertHtmlBlock(block, `season_plan.phases[${idx}].blocks[${blockIdx}]`);
    });
    validateDisclosureNodes(phase.nodes, `season_plan.phases[${idx}].nodes`);
  });
}

function validateWeeklyPlan(plan: UiWeeklyPlan): void {
  assertCondition(plan.type === "weekly_plan", "weekly_plan.type must be 'weekly_plan'");
  assertCondition(plan.schema_version > 0, "weekly_plan.schema_version must be > 0");
  assertString(plan.plan_id, "weekly_plan.plan_id");
  assertString(plan.athlete_name, "weekly_plan.athlete_name");

  const weeks = assertArray<UiWeekPlan>(plan.weeks, "weekly_plan.weeks");
  validateDisclosureNodes(plan.global_nodes, "weekly_plan.global_nodes");
  weeks.forEach((week, idx) => {
    assertString(week.week_id, `weekly_plan.weeks[${idx}].week_id`);
    assertString(week.start_date, `weekly_plan.weeks[${idx}].start_date`);
    assertString(week.end_date, `weekly_plan.weeks[${idx}].end_date`);

    assertArray<UiHtmlBlock>(week.notes_blocks, `weekly_plan.weeks[${idx}].notes_blocks`).forEach((block, blockIdx) => {
      assertHtmlBlock(block, `weekly_plan.weeks[${idx}].notes_blocks[${blockIdx}]`);
    });
    validateDisclosureNodes(week.notes_nodes, `weekly_plan.weeks[${idx}].notes_nodes`);

    const days = assertArray<UiWeekPlan["days"][number]>(week.days, `weekly_plan.weeks[${idx}].days`);
    days.forEach((day, dayIdx) => {
      assertString(day.day_id, `weekly_plan.weeks[${idx}].days[${dayIdx}].day_id`);
      assertString(day.date, `weekly_plan.weeks[${idx}].days[${dayIdx}].date`);
      assertArray<UiHtmlBlock>(day.blocks, `weekly_plan.weeks[${idx}].days[${dayIdx}].blocks`).forEach((block, blockIdx) => {
        assertHtmlBlock(block, `weekly_plan.weeks[${idx}].days[${dayIdx}].blocks[${blockIdx}]`);
      });
      validateDisclosureNodes(day.nodes, `weekly_plan.weeks[${idx}].days[${dayIdx}].nodes`);
    });
  });
}

const LEAK_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  {
    pattern: /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i,
    label: "email-like value",
  },
  {
    pattern: /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i,
    label: "uuid-like value",
  },
  {
    pattern: /\b(trace[_-]?id|root[_-]?run[_-]?id|run[_-]?id|source[_-]?job[_-]?id)\b/i,
    label: "trace/run identifier token",
  },
];

function assertNoLeakSignals(label: string, payload: unknown): void {
  const serialized = JSON.stringify(payload);
  LEAK_PATTERNS.forEach(({ pattern, label: leakLabel }) => {
    assertCondition(!pattern.test(serialized), `${label} contains prohibited ${leakLabel}`);
  });
}

type FixtureBundle = {
  personaId: DemoPersonaId;
  analysis: UiAnalysis;
  season: UiSeasonPlan;
  weekly: UiWeeklyPlan;
};

function assertPersonaRecord<T>(value: unknown, name: string): Record<DemoPersonaId, T> {
  assertCondition(typeof value === "object" && value !== null, `${name} must be an object`);
  const record = value as Record<string, T>;

  DEMO_PERSONA_IDS.forEach((personaId) => {
    assertCondition(personaId in record, `${name} is missing persona '${personaId}'`);
  });

  return record as Record<DemoPersonaId, T>;
}

async function loadFixtureBundles(versionDir: string): Promise<FixtureBundle[]> {
  const analysisModule = await import(pathToFileURL(join(versionDir, "analysis.ts")).href);
  const seasonModule = await import(pathToFileURL(join(versionDir, "season.ts")).href);
  const weeklyModule = await import(pathToFileURL(join(versionDir, "weekly.ts")).href);

  const analysisByPersona = assertPersonaRecord<UiAnalysis>(
    analysisModule.DEMO_ANALYSIS_BY_PERSONA,
    "DEMO_ANALYSIS_BY_PERSONA",
  );
  const seasonByPersona = assertPersonaRecord<UiSeasonPlan>(
    seasonModule.DEMO_SEASON_PLAN_BY_PERSONA,
    "DEMO_SEASON_PLAN_BY_PERSONA",
  );
  const weeklyByPersona = assertPersonaRecord<UiWeeklyPlan>(
    weeklyModule.DEMO_WEEKLY_PLAN_BY_PERSONA,
    "DEMO_WEEKLY_PLAN_BY_PERSONA",
  );

  return DEMO_PERSONA_IDS.map((personaId) => ({
    personaId,
    analysis: analysisByPersona[personaId],
    season: seasonByPersona[personaId],
    weekly: weeklyByPersona[personaId],
  }));
}

async function run() {
  assertCondition(
    resolveDemoPersonaId("invalid-persona-id") === DEFAULT_DEMO_PERSONA_ID,
    "resolveDemoPersonaId must fall back to the default persona for invalid input",
  );

  const currentDir = dirname(fileURLToPath(import.meta.url));
  const fixturesRoot = join(currentDir, "..", "..", "lib", "demo", "fixtures");
  const versionDirs = readdirSync(fixturesRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name.startsWith("v"))
    .map((entry) => join(fixturesRoot, entry.name));

  assertCondition(versionDirs.length > 0, "No versioned fixture directories found");
  const presentVersions = new Set(versionDirs.map((dir) => Number.parseInt(dir.split("/").at(-1)?.replace("v", "") ?? "", 10)));
  SUPPORTED_SCHEMA_VERSIONS.forEach((version) => {
    assertCondition(presentVersions.has(version), `Missing fixture directory for supported schema version v${version}`);
  });

  let validatedBundles = 0;

  for (const dir of versionDirs) {
    const bundles = await loadFixtureBundles(dir);

    for (const bundle of bundles) {
      validateAnalysis(bundle.analysis);
      validateSeasonPlan(bundle.season);
      validateWeeklyPlan(bundle.weekly);
      assertNoLeakSignals(`${dir}:${bundle.personaId}:analysis`, bundle.analysis);
      assertNoLeakSignals(`${dir}:${bundle.personaId}:season`, bundle.season);
      assertNoLeakSignals(`${dir}:${bundle.personaId}:weekly`, bundle.weekly);
      validatedBundles += 1;
    }
  }

  console.log(`Fixture validation passed for ${versionDirs.length} version(s) and ${validatedBundles} persona bundle(s).`);
}

run();
