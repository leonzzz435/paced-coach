import {
  CoachStreamServerError,
  parseSseFrame,
  readCoachTurnSse,
  type CoachTurnStatusEvent,
} from "../../components/coach-chat/coach-inbox-parts";

function assertCondition(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function sseFrame(eventName: string, data?: string): string {
  const lines = [`event: ${eventName}`];
  if (data !== undefined) {
    for (const line of data.split("\n")) {
      lines.push(`data: ${line}`);
    }
  }
  lines.push("");
  return `${lines.join("\n")}\n`;
}

function buildSseResponse(frames: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(frame));
      }
      controller.close();
    },
  });
  return new Response(body, { headers: { "Content-Type": "text/event-stream" } });
}

async function assertRejects(
  description: string,
  fn: () => Promise<unknown>,
  validateError: (error: unknown) => void,
): Promise<void> {
  let didThrow = false;
  try {
    await fn();
  } catch (error) {
    didThrow = true;
    validateError(error);
  }
  assertCondition(didThrow, `${description}: expected function to throw`);
}

function testParseSseFrameSupportsMultilineData(): void {
  const frame = `event: status\ndata: {"step":"thinking",\ndata: "message":"Using latest context"}\n\n`;
  const parsed = parseSseFrame(frame);
  assertCondition(parsed !== null, "Frame should parse");
  assertCondition(parsed?.event === "status", "Event should be status");
  assertCondition(
    parsed?.data === '{"step":"thinking",\n"message":"Using latest context"}',
    "Multiline data lines should be merged with newline delimiters",
  );
}

async function testReadCoachTurnSseReadsStatusAndResult(): Promise<void> {
  const statusPayload = '{"step":"thinking",\n"message":"Thinking through the next step","iteration":1}';
  const resultPayload = JSON.stringify({
    thread: {
      id: "thread-1",
      status: "active",
      title: "Test",
      latest_seq: 4,
      updated_at: "2026-02-28T12:00:00+00:00",
    },
    projection: {
      messages: [],
      quota: { week_anchor_utc: "", used: 0, limit: 0, remaining: 0, is_limited: false },
      can_send_message: true,
      coach_gate_message: null,
      coach_gate_target: null,
      has_pending_proposal: false,
      can_trigger_recap: true,
      training_provider_message: null,
      recap_gate_target: null,
      pending_proposal_ids: [],
      next_after_seq: 4,
    },
    events_appended: [{ seq: 4, event_type: "coach_message" }],
    turn: { kind: "message" },
  });
  const response = buildSseResponse([sseFrame("status", statusPayload), sseFrame("result", resultPayload), sseFrame("done")]);
  const seenStatuses: CoachTurnStatusEvent[] = [];

  const payload = await readCoachTurnSse(
    response,
    (statusEvent) => {
      seenStatuses.push(statusEvent);
    },
    {
      readTimeoutMs: 100,
      totalTimeoutMs: 1000,
      doneReadTimeoutMs: 100,
    },
  );

  assertCondition(seenStatuses.length === 1, "Expected one status event");
  assertCondition(seenStatuses[0].message === "Thinking through the next step", "Status message should match stream payload");
  assertCondition(payload.thread.id === "thread-1", "Result payload should be returned");
}

async function testReadCoachTurnSseRaisesServerErrorEvent(): Promise<void> {
  const response = buildSseResponse([sseFrame("error", JSON.stringify({ detail: "Tool failure", status_code: 500 })), sseFrame("done")]);

  await assertRejects(
    "server error frame",
    async () =>
      await readCoachTurnSse(response, () => undefined, {
        readTimeoutMs: 100,
        totalTimeoutMs: 1000,
        doneReadTimeoutMs: 100,
      }),
    (error) => {
      if (!(error instanceof CoachStreamServerError)) {
        throw new Error("Error should be CoachStreamServerError");
      }
      assertCondition(error.message === "Tool failure", "Server detail should be surfaced");
    },
  );
}

async function testReadCoachTurnSseFailsWhenResultMissing(): Promise<void> {
  const response = buildSseResponse([sseFrame("status", JSON.stringify({ step: "thinking", message: "Still working..." })), sseFrame("done")]);

  await assertRejects(
    "missing result frame",
    async () =>
      await readCoachTurnSse(response, () => undefined, {
        readTimeoutMs: 100,
        totalTimeoutMs: 1000,
        doneReadTimeoutMs: 100,
      }),
    (error) => {
      if (!(error instanceof Error)) {
        throw new Error("Expected Error instance");
      }
      assertCondition(error.message === "No result returned from coach stream", "Missing result error should be deterministic");
    },
  );
}

async function testReadCoachTurnSseFailsOnMalformedPayload(): Promise<void> {
  const response = buildSseResponse([sseFrame("status", "{bad json"), sseFrame("done")]);

  await assertRejects(
    "malformed status payload",
    async () =>
      await readCoachTurnSse(response, () => undefined, {
        readTimeoutMs: 100,
        totalTimeoutMs: 1000,
        doneReadTimeoutMs: 100,
      }),
    (error) => {
      assertCondition(error instanceof Error, "Expected regular Error");
      if (!(error instanceof Error)) {
        throw new Error("Expected Error instance");
      }
      assertCondition(error.message === "Malformed status event payload", "Malformed payload error should identify event type");
    },
  );
}

async function run(): Promise<void> {
  testParseSseFrameSupportsMultilineData();
  await testReadCoachTurnSseReadsStatusAndResult();
  await testReadCoachTurnSseRaisesServerErrorEvent();
  await testReadCoachTurnSseFailsWhenResultMissing();
  await testReadCoachTurnSseFailsOnMalformedPayload();
  console.log("Coach turn SSE parser tests passed.");
}

run();
