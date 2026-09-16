# Model selection

The app uses OpenAI's Responses API through its central model configuration.
Set `AI_MODE` in the root `.env`, then restart both the API and worker.

```dotenv
AI_MODE=astra
```

The opt-in `astra` mode assigns `gpt-6-astra` to the Head Coach and research
specialist. Supporting composition, memory and triage roles keep GPT-5.5. The
default `cost_effective` mode is unchanged. Access to a model depends on the
OpenAI project associated with your API key.

Model choice and task behavior are separate. Semantic run profiles determine
reasoning effort and tool access: routine planning and chat use `medium`,
material replanning and research use `xhigh`, and supporting tasks use `low`.
Web search is enabled only for the research profile.

The [GPT-6 Astra migration guide](https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra)
requires supported reasoning settings and excludes sampling parameters such as
`temperature` and `top_p`. The Astra configuration explicitly uses Responses,
sets a 128,000-token output ceiling, and does not send unsupported sampling
parameters. This is a ceiling, not a request to generate that many tokens.

Select models in `services/ai/ai_settings.py` and configure capabilities in
`services/ai/model_config.py`. Call sites select semantic run profiles instead
of embedding model IDs. Contract tests cover all Astra profiles, reasoning,
structured-output compatibility settings and research-only search.

Local-first describes the application and database. Model requests still send
relevant athlete context to OpenAI. See [privacy and data](privacy-and-data.md).
No cost or quality advantage is implied by selecting a newer model; consult the
release verification record for the exact checks performed.
